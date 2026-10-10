from calculator import add, subtract


def main():
    first_number = float(input("Enter the first number: "))
    second_number = float(input("Enter the second number: "))

    print(f"Addition: {add(first_number, second_number)}")
    print(f"Subtraction: {subtract(first_number, second_number)}")


if __name__ == "__main__":
    main()
