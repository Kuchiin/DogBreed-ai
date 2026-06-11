import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
import torchvision.transforms as transforms
from torchvision import models 
from PIL import Image
import io
import base64
import os
import json
import urllib.request
import urllib.error

app = FastAPI(title="Dog Breed Classifier - ConvNext")

# Włączamy CORS, aby nasza aplikacja kliencka (np. na Netlify) mogła wysyłać zapytania bezpośrednio do Hugging Face Spaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Constants from training ---
IMG_HEIGHT = 300
IMG_WIDTH = 300
NUM_CLASSES = 120 

# Dynamic path resolution to find the model weight file where 'main.py' is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "convnext_pytorch_finetuned.pth")

# --- Image Preprocessing (Inference version of your training transforms) ---
# To jest IDENTYCZNE z val_test_transforms z data_preprocessing.py
preprocess = transforms.Compose([
    transforms.Resize((IMG_HEIGHT, IMG_WIDTH)), # Zmieniono, aby pasowało do treningu
    transforms.ToTensor(),                     
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Initialize Architecture - Teraz dla ConvNeXt Small, ODTWARZAMY JAK W TRENINGU
model = models.convnext_small(weights=None) # Bez wag, bo wczytamy swoje

# === DOKŁADNE ODTWORZENIE GŁOWY KLASYFIKACYJNEJ Z train_model.py ===
# 1. Pobieramy in_features z oryginalnej ostatniej warstwy liniowej ConvNeXt
#    W standardowym ConvNeXt small, 'classifier' to Sequential(LayerNorm2d, Flatten, Linear)
#    Więc 'classifier[2]' to jest ta ostatnia warstwa liniowa, tak jak u Ciebie w treningu.
in_features = model.classifier[2].in_features 

# 2. Zastępujemy CAŁY 'model.classifier' naszą sekwencją warstw
#    Te warstwy MUSZĄ być IDENTYCZNE z tymi z train_model.py
model.classifier = torch.nn.Sequential(
    torch.nn.Flatten(1),
    torch.nn.LayerNorm(in_features),
    torch.nn.Linear(in_features, 512), # Liczba neuronów 512, jak w treningu
    torch.nn.GELU(),
    torch.nn.Dropout(0.3), # Dropout 0.3, jak w treningu
    torch.nn.Linear(512, NUM_CLASSES)
)

MODEL_LOADED = False

if os.path.exists(MODEL_PATH):
    print(f"Wczytywanie wag z {MODEL_PATH}...")
    try:
        # Load state_dict (weights)
        state_dict = torch.load(MODEL_PATH, map_location=device)
        model.load_state_dict(state_dict)
        model.to(device)
        model.eval() # Ustawiamy model w tryb ewaluacji
        MODEL_LOADED = True
        print("Model wczytany pomyślnie!")
    except Exception as e:
        print(f"Błąd podczas wczytywania wag modelu: {e}")
        raise RuntimeError(f"Nie udało się wczytać wag modelu: {e}")
else:
    print(f"BŁĄD KRYTYCZNY: Plik wag modelu {MODEL_PATH} nie został znaleziony. Aplikacja nie może działać poprawnie.")
    raise FileNotFoundError(f"Plik wag modelu {MODEL_PATH} nie został znaleziony.")

@app.get("/health")
async def health():
    print("Healthcheck endpoint pinged!")
    return {
        "status": "ready" if MODEL_LOADED else "error",
        "model_file": MODEL_PATH,
        "exists": os.path.exists(MODEL_PATH),
        "device": str(device)
    }

# --- Class Names ---
# WAŻNE: TA LISTA MUSI BYĆ DOKŁADNIE TAKA SAMA I W TEJ SAMEJ KOLEJNOŚCI, JAK w `class_names` z `data_preprocessing.py`
BREEDS = ['Chihuahua', 'Japanese Spaniel', 'Maltese Dog', 'Pekinese', 'Tzu', 'Blenheim Spaniel', 'Papillon', 'Toy Terrier', 
          'Rhodesian Ridgeback', 'Afghan Hound', 'Basset', 'Beagle', 'Bloodhound', 'Bluetick', 'Tan Coonhound', 'Walker Hound', 
          'English Foxhound', 'Redbone', 'Borzoi', 'Irish Wolfhound', 'Italian Greyhound', 'Whippet', 'Ibizan Hound', 
          'Norwegian Elkhound', 'Otterhound', 'Saluki', 'Scottish Deerhound', 'Weimaraner', 'Staffordshire Bullterrier', 
          'American Staffordshire Terrier', 'Bedlington Terrier', 'Border Terrier', 'Kerry Blue Terrier', 'Irish Terrier', 
          'Norfolk Terrier', 'Norwich Terrier', 'Yorkshire Terrier', 'Haired Fox Terrier', 'Lakeland Terrier', 'Sealyham Terrier', 
          'Airedale', 'Cairn', 'Australian Terrier', 'Dandie Dinmont', 'Boston Bull', 'Miniature Schnauzer', 'Giant Schnauzer', 
          'Standard Schnauzer', 'Scotch Terrier', 'Tibetan Terrier', 'Silky Terrier', 'Coated Wheaten Terrier', 
          'West Highland White Terrier', 'Lhasa', 'Coated Retriever', 'Coated Retriever', 'Golden Retriever', 
          'Labrador Retriever', 'Chesapeake Bay Retriever', 'Haired Pointer', 'Vizsla', 'English Setter', 'Irish Setter', 
          'Gordon Setter', 'Brittany Spaniel', 'Clumber', 'English Springer', 'Welsh Springer Spaniel', 'Cocker Spaniel', 
          'Sussex Spaniel', 'Irish Water Spaniel', 'Kuvasz', 'Schipperke', 'Groenendael', 'Malinois', 'Briard', 'Kelpie', 
          'Komondor', 'Old English Sheepdog', 'Shetland Sheepdog', 'Collie', 'Border Collie', 'Bouvier Des Flandres', 'Rottweiler', 
          'German Shepherd', 'Doberman', 'Miniature Pinscher', 'Greater Swiss Mountain Dog', 'Bernese Mountain Dog', 'Appenzeller', 
          'Entlebucher', 'Boxer', 'Bull Mastiff', 'Tibetan Mastiff', 'French Bulldog', 'Great Dane', 'Saint Bernard', 'Eskimo Dog', 
          'Malamute', 'Siberian Husky', 'Affenpinscher', 'Basenji', 'Pug', 'Leonberg', 'Newfoundland', 'Great Pyrenees', 'Samoyed', 
          'Pomeranian', 'Chow', 'Keeshond', 'Brabancon Griffon', 'Pembroke', 'Cardigan', 'Toy Poodle', 'Miniature Poodle', 
          'Standard Poodle', 'Mexican Hairless', 'Dingo', 'Dhole', 'African Hunting Dog']

class ImageInput(BaseModel):
    image: str # Base64 encoded image

@app.post("/predict")
async def predict(data: ImageInput):
    try:
        # Decode base64 image
        header, encoded = data.image.split(",", 1) if "," in data.image else (None, data.image)
        image_data = base64.b64decode(encoded)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        # Preprocess
        input_tensor = preprocess(image)
        input_batch = input_tensor.unsqueeze(0).to(device)
        
        # Inference
        with torch.no_grad():
            output = model(input_batch)
            probabilities = torch.nn.functional.softmax(output[0], dim=0)
            
        # Get Top 1
        confidence, index = torch.max(probabilities, 0)
        breed_index = index.item()
        
        display_breed = BREEDS[breed_index] # Pobieramy nazwę rasy bezpośrednio
        
        return {
            "breed": display_breed,
            "confidence": round(confidence.item() * 100, 2),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class DescriptionInput(BaseModel):
    breed: str
    lang: str = "pl"

@app.post("/description")
async def description(data: DescriptionInput):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Brak klucza API Gemini na serwerze (GEMINI_API_KEY). Skonfiguruj go w ustawieniach Hugging Face."
        )

    is_english = data.lang == "en"
    if is_english:
        prompt_text = f"Write a few interesting, engaging sentences about the dog breed {data.breed} in English. List its primary characteristics or fun facts. Use simple markdown formatting (like bold text or bullet points) to make it highly readable."
    else:
        prompt_text = f"Napisz parę ciekawych, angażujących zdań o psie rasy {data.breed} po polsku. Wymień jego główne cechy charakteru lub ciekawostki. Użyj prostego formatowania markdown (np. pogrubienia lub listy punktowej), aby tekst był bardzo czytelny."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    req_data = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    req_body = json.dumps(req_data).encode("utf-8")
    req_headers = {"Content-Type": "application/json", "User-Agent": "aistudio-build"}
    req = urllib.request.Request(url, data=req_body, headers=req_headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode("utf-8")
            res_data = json.loads(res_body)
            try:
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return {"description": text}
            except (KeyError, IndexError):
                print(f"Błąd struktury odpowiedzi Gemini: {res_data}")
                raise HTTPException(status_code=502, detail="Nietypowa odpowiedź z API Gemini.")
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"HTTPError gemini: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Błąd API Gemini: {error_msg}")
    except Exception as e:
        print(f"Exception gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Błąd połączenia z Gemini: {str(e)}")

if __name__ == "__main__":
    # Hugging Face Spaces passes the port via the PORT environment variable (usually 7860)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
