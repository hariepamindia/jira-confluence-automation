$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8

$supportedProtocolVersions = @(
    "2025-11-25",
    "2025-06-18",
    "2025-03-26",
    "2024-11-05"
)

function Write-JsonRpcResponse {
    param(
        [AllowNull()]
        [object] $Id,
        [object] $Result
    )

    $response = @{
        jsonrpc = "2.0"
        id      = $Id
        result  = $Result
    }
    [Console]::Out.WriteLine(($response | ConvertTo-Json -Depth 20 -Compress))
}

function Write-JsonRpcError {
    param(
        [AllowNull()]
        [object] $Id,
        [int] $Code,
        [string] $Message
    )

    $response = @{
        jsonrpc = "2.0"
        id      = $Id
        error   = @{
            code    = $Code
            message = $Message
        }
    }
    [Console]::Out.WriteLine(($response | ConvertTo-Json -Depth 20 -Compress))
}

function Write-ToolResult {
    param(
        [object] $Id,
        [string] $Text,
        [bool] $IsError = $false
    )

    Write-JsonRpcResponse -Id $Id -Result @{
        content = @(
            @{
                type = "text"
                text = $Text
            }
        )
        isError = $IsError
    }
}

function Test-JsonNumber {
    param([object] $Value)

    if ($null -eq $Value -or $Value -is [bool]) {
        return $false
    }

    $typeCode = [System.Type]::GetTypeCode($Value.GetType())
    return ($typeCode -in @(
        [System.TypeCode]::SByte,
        [System.TypeCode]::Byte,
        [System.TypeCode]::Int16,
        [System.TypeCode]::UInt16,
        [System.TypeCode]::Int32,
        [System.TypeCode]::UInt32,
        [System.TypeCode]::Int64,
        [System.TypeCode]::UInt64,
        [System.TypeCode]::Single,
        [System.TypeCode]::Double,
        [System.TypeCode]::Decimal
    ))
}

function Get-ToolDefinitions {
    return @(
        @{
            name        = "echo"
            description = "Returns the provided message unchanged."
            inputSchema = @{
                type                 = "object"
                properties           = @{
                    message = @{
                        type        = "string"
                        description = "The message to echo."
                    }
                }
                required             = @("message")
                additionalProperties = $false
            }
        },
        @{
            name        = "get_time"
            description = "Returns the current time in UTC using ISO 8601 format."
            inputSchema = @{
                type                 = "object"
                properties           = @{}
                additionalProperties = $false
            }
        },
        @{
            name        = "calculate"
            description = "Calculates the result of an arithmetic operation on two numbers."
            inputSchema = @{
                type                 = "object"
                properties           = @{
                    operation = @{
                        type        = "string"
                        description = "The arithmetic operation to perform."
                        enum        = @("add", "subtract", "multiply", "divide")
                    }
                    a         = @{
                        type        = "number"
                        description = "The first operand."
                    }
                    b         = @{
                        type        = "number"
                        description = "The second operand."
                    }
                }
                required             = @("operation", "a", "b")
                additionalProperties = $false
            }
        }
    )
}

function Get-ToolArgumentsError {
    param(
        [string] $ToolName,
        [object] $Arguments
    )

    if (@("echo", "get_time", "calculate") -notcontains $ToolName) {
        return "Unknown tool: $ToolName"
    }

    if ($null -eq $Arguments -or
        $Arguments -isnot [System.Management.Automation.PSCustomObject]) {
        return "The '$ToolName' tool requires an arguments object."
    }

    $argumentNames = @($Arguments.PSObject.Properties | ForEach-Object { $_.Name })
    switch ($ToolName) {
        "echo" {
            if ($argumentNames -notcontains "message" -or $Arguments.message -isnot [string]) {
                return "The echo tool requires a string 'message' argument."
            }
            if ($argumentNames.Count -ne 1) {
                return "The echo tool accepts only the 'message' argument."
            }
        }
        "get_time" {
            if ($argumentNames.Count -ne 0) {
                return "The get_time tool does not accept arguments."
            }
        }
        "calculate" {
            if ($argumentNames -notcontains "operation" -or
                $Arguments.operation -isnot [string] -or
                @("add", "subtract", "multiply", "divide") -notcontains $Arguments.operation) {
                return "The calculate tool requires an 'operation' of add, subtract, multiply, or divide."
            }
            if ($argumentNames -notcontains "a" -or -not (Test-JsonNumber -Value $Arguments.a) -or
                $argumentNames -notcontains "b" -or -not (Test-JsonNumber -Value $Arguments.b)) {
                return "The calculate tool requires numeric 'a' and 'b' arguments."
            }
            if ($argumentNames.Count -ne 3) {
                return "The calculate tool accepts only 'operation', 'a', and 'b' arguments."
            }
        }
    }

    return $null
}

$shutdownRequested = $false
while (-not $shutdownRequested) {
    $line = [Console]::In.ReadLine()
    if ($null -eq $line) {
        break
    }

    try {
        $request = ConvertFrom-Json -InputObject $line -ErrorAction Stop
    }
    catch {
        Write-JsonRpcError -Id $null -Code -32700 -Message "Parse error"
        continue
    }

    $method = $request.method
    $requestId = $request.id
    $hasRequestId = $request.PSObject.Properties.Name -contains "id"

    switch ($method) {
        "initialize" {
            $requestedVersion = $request.params.protocolVersion
            if ($supportedProtocolVersions -contains $requestedVersion) {
                $protocolVersion = $requestedVersion
            }
            else {
                $protocolVersion = $supportedProtocolVersions[0]
            }

            if ($hasRequestId) {
                Write-JsonRpcResponse -Id $requestId -Result @{
                    protocolVersion = $protocolVersion
                    capabilities    = @{
                        tools = @{
                            listChanged = $false
                        }
                    }
                    serverInfo      = @{
                        name    = "mcp-echo"
                        version = "1.0.0"
                    }
                }
            }
        }
        "notifications/initialized" {
        }
        "ping" {
            if ($hasRequestId) {
                Write-JsonRpcResponse -Id $requestId -Result @{}
            }
        }
        "tools/list" {
            if ($hasRequestId) {
                Write-JsonRpcResponse -Id $requestId -Result @{
                    tools = @(Get-ToolDefinitions)
                }
            }
        }
        "tools/call" {
            if (-not $hasRequestId) {
                continue
            }

            $toolName = $request.params.name
            $arguments = $request.params.arguments
            $argumentError = Get-ToolArgumentsError -ToolName $toolName -Arguments $arguments
            if ($null -ne $argumentError) {
                Write-ToolResult -Id $requestId -Text $argumentError -IsError $true
                continue
            }

            switch ($toolName) {
                "echo" {
                    Write-ToolResult -Id $requestId -Text $arguments.message
                }
                "get_time" {
                    $utcTime = [System.DateTime]::UtcNow.ToString(
                        "o",
                        [System.Globalization.CultureInfo]::InvariantCulture
                    )
                    Write-ToolResult -Id $requestId -Text $utcTime
                }
                "calculate" {
                    $first = [System.Convert]::ToDouble(
                        $arguments.a,
                        [System.Globalization.CultureInfo]::InvariantCulture
                    )
                    $second = [System.Convert]::ToDouble(
                        $arguments.b,
                        [System.Globalization.CultureInfo]::InvariantCulture
                    )

                    if ([double]::IsNaN($first) -or [double]::IsInfinity($first) -or
                        [double]::IsNaN($second) -or [double]::IsInfinity($second)) {
                        Write-ToolResult -Id $requestId -Text "The operands must be finite numbers." -IsError $true
                        continue
                    }

                    if ($toolName -eq "divide" -and $second -eq 0) {
                        Write-ToolResult -Id $requestId -Text "Division by zero is not allowed." -IsError $true
                        continue
                    }

                    switch ($arguments.operation) {
                        "add"      { $value = $first + $second }
                        "subtract" { $value = $first - $second }
                        "multiply" { $value = $first * $second }
                        "divide"   { $value = $first / $second }
                    }

                    if ([double]::IsNaN($value) -or [double]::IsInfinity($value)) {
                        Write-ToolResult -Id $requestId -Text "The result is outside the supported numeric range." -IsError $true
                        continue
                    }

                    $formattedValue = $value.ToString(
                        "G",
                        [System.Globalization.CultureInfo]::InvariantCulture
                    )
                    Write-ToolResult -Id $requestId -Text $formattedValue
                }
            }
        }
        "shutdown" {
            if ($hasRequestId) {
                Write-JsonRpcResponse -Id $requestId -Result $null
            }
        }
        "exit" {
            $shutdownRequested = $true
        }
        default {
            if ($hasRequestId) {
                Write-JsonRpcError -Id $requestId -Code -32601 -Message "Method not found"
            }
        }
    }
}