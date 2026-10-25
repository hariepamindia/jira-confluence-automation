import React, { useState } from "react";

function App() {
  const [message, setMessage] = useState("");

  const generateReport = () => {
    setMessage("Report generated successfully.");
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial, sans-serif" }}>
      <h1>Jira/Confluence Automation</h1>

      <p>Frontend prototype is running successfully.</p>

      <h2>Status</h2>

      <ul>
        <li>React frontend ✅</li>
        <li>Vite development server ✅</li>
        <li>Chrome DevTools MCP ✅</li>
        <li>QA testing enabled ✅</li>
      </ul>

      <button onClick={generateReport}>
        Generate Report
      </button>

      {message && (
        <p style={{ marginTop: "1rem", color: "green" }}>
          {message}
        </p>
      )}
    </div>
  );
}

export default App;