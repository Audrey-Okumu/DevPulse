def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price']
    return total

def divide(a, b):
    return a / b

API_KEY = "sk-12345-hardcoded-secret"
