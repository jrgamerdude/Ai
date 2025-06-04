import random

def main():
    number = random.randint(1, 100)
    print("I'm thinking of a number between 1 and 100.")
    attempts = 0
    while True:
        guess = input("Take a guess: ")
        attempts += 1
        try:
            guess = int(guess)
        except ValueError:
            print("Please enter a valid integer.")
            continue
        if guess < number:
            print("Too low!")
        elif guess > number:
            print("Too high!")
        else:
            print(f"Correct! You guessed it in {attempts} attempts.")
            break

if __name__ == "__main__":
    main()
