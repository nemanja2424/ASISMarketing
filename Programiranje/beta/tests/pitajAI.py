import requests

# Tvoj lokalni LLaMA server
url = "http://127.0.0.1:1234/v1/completions"

# Model koji koristiš
model = "openai/gpt-oss-20b"

# Ovde menjaš poruku koju želiš da pošalješ
poruka = "Da li mozes da analiziras .json fajl, odnosno da li mogu da ti predlozim bas fajl?"

data = {
    "model": model,
    "prompt": poruka,
    "max_tokens": 200
}

try:
    response = requests.post(url, json=data)
    response.raise_for_status()  # baci grešku ako nije 200 OK
    result = response.json()
    # Pretpostavljamo da server vraća OpenAI-like 'choices'
    odgovor = result['choices'][0]['text']
    print("Odgovor modela:", odgovor.strip())
except Exception as e:
    print("Došlo je do greške:", e)
