from fanar_client import ask_fanar

if __name__ == "__main__":
    prompt=input("prompt:\t")
    response = ask_fanar(prompt)
    print("\nResponse:\n")
    print(response)