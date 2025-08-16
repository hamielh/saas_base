import requests

url = "http://localhost:5000/api/create-user"

payload = {
    "email": "hamielhenrique29@gmail.com",
    "password": "123456",
    "first_name": "Admin",
    "last_name": "Sistema",
    "role": "super_admin"
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print("Status Code:", response.status_code)
print("Resposta:", response.text)
