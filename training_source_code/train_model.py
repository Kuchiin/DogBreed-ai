import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models
import matplotlib.pyplot as plt
import numpy as np
import time
from torch.optim.lr_scheduler import ReduceLROnPlateau 

# Importujemy naszą funkcję do ładowania i preprocessingu danych oraz DEVICE
from data_preprocessing import load_and_preprocess_data, IMG_HEIGHT, IMG_WIDTH, DEVICE, BATCH_SIZE

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

DATA_DIR = 'projekt01/Images_of_dogs'
MODEL_SAVE_PATH = 'projekt01/models/mobilenetv2_pytorch_finetuned_v5.pth'

# === ŁADOWANIE I PRZYGOTOWANIE DANYCH ===
train_loader, val_loader, test_loader, num_classes, class_names, class_to_idx = load_and_preprocess_data(DATA_DIR)
print("\nDataLoadery załadowane z data_preprocessing.py.")

# === DEFINICJA MODELU Z TRANSFER LEARNING (MobileNetV2) ===
print("\nŁadowanie modelu bazowego MobileNetV2 (PyTorch)...")

model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)

# Zamrożenie WSZYSTKICH parametrów modelu bazowego na początek
for param in model.parameters():
    param.requires_grad = False
print("Wszystkie warstwy modelu bazowego MobileNetV2 zamrożone dla początkowego treningu.")

# Zastąpienie ostatniej warstwy klasyfikacyjnej i dodanie Dropout
num_ftrs = model.classifier[1].in_features
# Zmieniona głowa klasyfikacyjna: mniej agresywny Dropout, więcej neuronów
model.classifier = nn.Sequential(
    nn.Dropout(0.3), # Mniej agresywny Dropout
    nn.Linear(num_ftrs, 512), # Więcej neuronów
    nn.ReLU(),
    nn.Dropout(0.2), # Mniej agresywny Dropout
    nn.Linear(512, num_classes)
)



# Przeniesienie modelu na wybrane urządzenie (GPU/CPU)
model = model.to(DEVICE)
print(f"Model MobileNetV2 zbudowany i przeniesiony na {DEVICE}.")

# === DEKLARACJA OPTIMIZERA I FUNKCJI STRATY ===
# W Faza 1 trenujemy tylko nową głowę (czyli model.classifier)
optimizer_ft_head = optim.Adam(model.classifier.parameters(), lr=0.001, weight_decay=1e-4) # Zwiększone weight_decay
criterion = nn.CrossEntropyLoss()

print("Optimizer (Adam) i funkcja straty (CrossEntropyLoss) skonfigurowane.")
print("\nGotowi do treningu!")

# === TRENING MODELU - FAZA 1: Trenowanie głowy klasyfikacyjnej ===
print("\n--- Rozpoczynanie TRENINGU FAZY 1: Trenowanie głowy klasyfikacyjnej ---")

EPOCHS_PHASE1 = 10 # Zwiększona liczba epok dla fazy 1
history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
best_val_accuracy = 0.0
start_time = time.time()

for epoch in range(EPOCHS_PHASE1):
    model.train()
    running_loss = 0.0
    correct_train = 0
    total_train = 0

    for inputs, labels in train_loader:
        inputs = inputs.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer_ft_head.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer_ft_head.step()

        running_loss += loss.item() * inputs.size(0)
        _, predicted = torch.max(outputs.data, 1)
        total_train += labels.size(0)
        correct_train += (predicted == labels).sum().item()

    epoch_train_loss = running_loss / len(train_loader.dataset)
    epoch_train_acc = correct_train / total_train
    
    model.eval()
    val_loss = 0.0
    correct_val = 0
    total_val = 0

    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs = inputs.to(DEVICE)
            labels = labels.to(DEVICE)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            val_loss += loss.item() * inputs.size(0)
            _, predicted = torch.max(outputs.data, 1)
            total_val += labels.size(0)
            correct_val += (predicted == labels).sum().item()

    epoch_val_loss = val_loss / len(val_loader.dataset)
    epoch_val_acc = correct_val / total_val

    history['train_loss'].append(epoch_train_loss)
    history['val_loss'].append(epoch_val_loss)
    history['train_acc'].append(epoch_train_acc)
    history['val_acc'].append(epoch_val_acc)

    print(f"Phase 1 - Epoch {epoch+1}/{EPOCHS_PHASE1} | "
          f"Train Loss: {epoch_train_loss:.4f} | Train Acc: {epoch_train_acc:.4f} | "
          f"Val Loss: {epoch_val_loss:.4f} | Val Acc: {epoch_val_acc:.4f}")

    if epoch_val_acc > best_val_accuracy:
        best_val_accuracy = epoch_val_acc
        os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
        torch.save(model.state_dict(), MODEL_SAVE_PATH)
        print(f"    -> Zapisano najlepszy model Fazy 1 z Val Acc: {best_val_accuracy:.4f}")

end_time_phase1 = time.time()
print(f"\n--- FAZA 1 Trening zakończony w {(end_time_phase1 - start_time):.2f} sekund ---")

# === TRENING MODELU - FAZA 2: Fine-tuning (odmrażanie i trenowanie CAŁEGO MODELU) ===
print("\n--- Rozpoczynanie TRENINGU FAZY 2: Fine-tuning całego modelu ---")

# WAŻNA ZMIANA: Odmrażamy TYLKO OSTATNIE DWA BLOKI konwolucyjne (features[17], features[18])
# Zamiast trzech, testujemy dwa, co powinno być mniej agresywne
for param in model.features[17:].parameters(): # Odmrażamy od bloku 17 do końca!
    param.requires_grad = True
print("Ostatnie 2 bloki (features[17:]) MobileNetV2 odmrożone.")

optimizer_ft_full = optim.Adam(model.parameters(), lr=0.000001, weight_decay=5e-4)

# Dodajemy scheduler współczynnika uczenia!
scheduler = ReduceLROnPlateau(optimizer_ft_full, mode='max', factor=0.1, patience=5)


EPOCHS_PHASE2 = 30 
current_epochs_trained = EPOCHS_PHASE1

# Wczytanie najlepszego modelu z Fazy 1
model.load_state_dict(torch.load(MODEL_SAVE_PATH))
model.to(DEVICE)

start_time_phase2 = time.time()

for epoch in range(EPOCHS_PHASE2):
    model.train()
    running_loss = 0.0
    correct_train = 0
    total_train = 0

    for inputs, labels in train_loader:
        inputs = inputs.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer_ft_full.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer_ft_full.step()

        running_loss += loss.item() * inputs.size(0)
        _, predicted = torch.max(outputs.data, 1)
        total_train += labels.size(0)
        correct_train += (predicted == labels).sum().item()

    epoch_train_loss = running_loss / len(train_loader.dataset)
    epoch_train_acc = correct_train / total_train
    
    model.eval()
    val_loss = 0.0
    correct_val = 0
    total_val = 0

    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs = inputs.to(DEVICE)
            labels = labels.to(DEVICE)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            val_loss += loss.item() * inputs.size(0)
            _, predicted = torch.max(outputs.data, 1)
            total_val += labels.size(0)
            correct_val += (predicted == labels).sum().item()

    epoch_val_loss = val_loss / len(val_loader.dataset)
    epoch_val_acc = correct_val / total_val

    history['train_loss'].append(epoch_train_loss)
    history['val_loss'].append(epoch_val_loss)
    history['train_acc'].append(epoch_train_acc)
    history['val_acc'].append(epoch_val_acc)

    print(f"Phase 2 - Epoch {epoch+1}/{EPOCHS_PHASE2} (Total {current_epochs_trained + epoch+1}/{EPOCHS_PHASE1 + EPOCHS_PHASE2}) | "
          f"Train Loss: {epoch_train_loss:.4f} | Train Acc: {epoch_train_acc:.4f} | "
          f"Val Loss: {epoch_val_loss:.4f} | Val Acc: {epoch_val_acc:.4f}")
    
    # Krok dla schedulera!
    scheduler.step(epoch_val_acc) # Scheduler monitoruje Val Accuracy

    if epoch_val_acc > best_val_accuracy:
        best_val_accuracy = epoch_val_acc
        torch.save(model.state_dict(), MODEL_SAVE_PATH)
        print(f"    -> Zapisano najlepszy model z Val Acc: {best_val_accuracy:.4f} do {MODEL_SAVE_PATH}")



end_time_phase2 = time.time()
print(f"\n--- FAZA 2 Trening zakończony w {(end_time_phase2 - start_time_phase2):.2f} sekund ---")
print(f"Całkowity czas treningu: {(end_time_phase2 - start_time):.2f} sekund ---")


# === WIZUALIZACJA WYNIKÓW TRENINGU (krzywe uczenia) ===
print("\nWizualizacja krzywych uczenia...")

total_epochs = EPOCHS_PHASE1 + EPOCHS_PHASE2

plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(range(total_epochs), history['train_acc'], label='Training Accuracy')
plt.plot(range(total_epochs), history['val_acc'], label='Validation Accuracy')
plt.legend(loc='lower right')
plt.title('Training and Validation Accuracy')

plt.subplot(1, 2, 2)
plt.plot(range(total_epochs), history['train_loss'], label='Training Loss')
plt.plot(range(total_epochs), history['val_loss'], label='Validation Loss')
plt.legend(loc='upper right')
plt.title('Training and Validation Loss')
plt.savefig('projekt01/wykresy/krzywe_uczenia_pytorch_finetuned_v5.png') # Nowa nazwa pliku wykresu
plt.close()

print("\n--- Model wytrenowany i krzywe uczenia wyświetlone ---")

# === OCENA NA ZBIORZE TESTOWYM ===
print("\nOcena modelu na zbiorze testowym...")

model.load_state_dict(torch.load(MODEL_SAVE_PATH)) # Wczytaj najlepszy model
model.eval()

test_loss = 0.0
correct_test = 0
total_test = 0

with torch.no_grad():
    for inputs, labels in test_loader:
        inputs = inputs.to(DEVICE)
        labels = labels.to(DEVICE)
        outputs = model(inputs)
        loss = criterion(outputs, labels)

        test_loss += loss.item() * inputs.size(0)
        _, predicted = torch.max(outputs.data, 1)
        total_test += labels.size(0)
        correct_test += (predicted == labels).sum().item()

final_test_loss = test_loss / len(test_loader.dataset)
final_test_accuracy = correct_test / total_test

print(f"Test Loss: {final_test_loss:.4f}")
print(f"Test Accuracy: {final_test_accuracy:.4f}")
print("\n--- Ocena na zbiorze testowym zakończona ---")