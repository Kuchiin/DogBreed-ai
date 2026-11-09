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
# Zmieniamy ścieżki zapisu dla nowego modelu
MODEL_SAVE_PATH = 'projekt01/models/convnext_pytorch_finetuned.pth'
HISTORY_SAVE_PATH = 'projekt01/history/convnext_history.npy' # Do zapisu historii, by później porównać
PLOT_SAVE_PATH = 'projekt01/wykresy/krzywe_uczenia_convnext_finetuned.png'

# === ŁADOWANIE I PRZYGOTOWANIE DANYCH ===
train_loader, val_loader, test_loader, num_classes, class_names, class_to_idx = load_and_preprocess_data(DATA_DIR)
print("\nDataLoadery załadowane z data_preprocessing.py.")

# === FUNKCJA DO TWORZENIA MODELU (teraz elastyczniej) ===
def create_model(model_name, num_classes):
    model = None

    if model_name == "mobilenetv2":
        model = models.mobilenet_v2(
            weights=models.MobileNetV2_Weights.IMAGENET1K_V1
        )

        # Zamrażamy wszystkie warstwy bazowe
        for param in model.parameters():
            param.requires_grad = False

        num_ftrs = model.classifier[1].in_features

        model.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(num_ftrs, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, num_classes)
        )

        print("Model MobileNetV2 zbudowany.")

        # Nazwa bloku do odmrożenia
        return model, "mobilenetv2"

    elif model_name == "resnet50":
        model = models.resnet50(
            weights=models.ResNet50_Weights.IMAGENET1K_V1
        )

        # Zamrażamy wszystkie warstwy bazowe
        for param in model.parameters():
            param.requires_grad = False

        num_ftrs = model.fc.in_features

        model.fc = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(num_ftrs, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, num_classes)
        )

        print("Model ResNet50 zbudowany.")

        # Ostatni blok ResNet
        return model, "resnet50"

    elif model_name == "efficientnet_b2":
        model = models.efficientnet_b2(
            weights=models.EfficientNet_B2_Weights.IMAGENET1K_V1
        )

        # Zamrażamy backbone
        for param in model.parameters():
            param.requires_grad = False

        num_ftrs = model.classifier[1].in_features

        model.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(num_ftrs, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )

        print("Model EfficientNet-B2 zbudowany.")

        # Do późniejszego odmrożenia
        return model, "efficientnet_b2"

    elif model_name == "convnext_small":
        model = models.convnext_small(
            weights=models.ConvNeXt_Small_Weights.IMAGENET1K_V1
        )

        # Zamrażamy backbone
        for param in model.parameters():
            param.requires_grad = False

        num_ftrs = model.classifier[2].in_features

        model.classifier = nn.Sequential(
         nn.Flatten(1),
         nn.LayerNorm(num_ftrs),
         nn.Linear(num_ftrs, 512),
         nn.GELU(),
         nn.Dropout(0.3),
         nn.Linear(512, num_classes)
        )

        print("Model ConvNeXt-Small zbudowany.")

        # Do późniejszego odmrożenia
        return model, "convnext_small"

    else:
        raise ValueError(
            "Nieznana nazwa modelu. "
            "Dostępne: mobilenetv2, resnet50, "
            "efficientnet_b2, convnext_small"
        )

# === WYBÓR I BUDOWA MODELU ===
# Zmieniamy tutaj, aby wybrać model, który chcemy trenować
# current_model_name = "mobilenetv2"
current_model_name = "convnext_small"

model, block_to_unfreeze_name = create_model(current_model_name, num_classes)
model = model.to(DEVICE)
print(f"Model {current_model_name} przeniesiony na {DEVICE}.")

# === DEKLARACJA OPTIMIZERA I FUNKCJI STRATY ===
# W Faza 1 trenujemy tylko nową głowę (model.classifier dla MobileNetV2, model.fc dla ResNet50)
optimizer_ft_head = optim.AdamW(
    filter(lambda p: p.requires_grad, model.parameters()),
    lr=0.001,
    weight_decay=1e-4
)
criterion = nn.CrossEntropyLoss()

print("Optimizer (AdamW) i funkcja straty (CrossEntropyLoss) skonfigurowane.")
print("\nGotowi do treningu!")

# === TRENING MODELU - FAZA 1: Trenowanie głowy klasyfikacyjnej ===
print(f"\n--- Rozpoczynanie TRENINGU FAZY 1 ({current_model_name}): Trenowanie głowy klasyfikacyjnej ---")

EPOCHS_PHASE1 = 10 
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
print(f"\n--- Rozpoczynanie TRENINGU FAZY 2 ({current_model_name}): Fine-tuning całego modelu ---")

if block_to_unfreeze_name == "mobilenetv2":
    for param in model.features[17:].parameters(): # Dla MobileNetV2 ostatnie 2 bloki
        param.requires_grad = True
    print("Ostatnie 2 bloki (features[17:]) MobileNetV2 odmrożone.")
elif block_to_unfreeze_name == "resnet50":
    for param in model.layer4.parameters(): # Dla ResNet50 ostatni blok konwolucyjny to layer4
        param.requires_grad = True
    print("Ostatni blok (layer4) ResNet50 odmrożony.")
elif block_to_unfreeze_name == "efficientnet_b2":
    for param in model.features[-3:].parameters():
        param.requires_grad = True

    print("Ostatnie bloki EfficientNet-B2 odmrożone.")
elif block_to_unfreeze_name == "convnext_small":
    # ConvNeXt ma stage-based features -> najlepszy fine-tuning = ostatni stage
    for param in model.features[-1].parameters():
        param.requires_grad = True

    print("Ostatni stage ConvNeXt-Small odmrożony.")


#optymalizatorktóry obejmuje wszystkie trenowalne parametry
optimizer_ft_full = optim.AdamW(
    filter(lambda p: p.requires_grad, model.parameters()),
    lr=5e-5,
    weight_decay=5e-4
)
scheduler = ReduceLROnPlateau(
    optimizer_ft_full,
    mode='min',
    factor=0.1,
    patience=2
)

EPOCHS_PHASE2 = 30 #liczba epok dla Fazy 2 (łącznie 10 + 30 = 40 epok)
current_epochs_trained = EPOCHS_PHASE1

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
    
    scheduler.step(epoch_val_acc)

    if epoch_val_acc > best_val_accuracy:
        best_val_accuracy = epoch_val_acc
        torch.save(model.state_dict(), MODEL_SAVE_PATH)
        print(f"    -> Zapisano najlepszy model z Val Acc: {best_val_accuracy:.4f} do {MODEL_SAVE_PATH}")

end_time_phase2 = time.time()
print(f"\n--- FAZA 2 Trening zakończony w {(end_time_phase2 - start_time_phase2):.2f} sekund ---")
print(f"Całkowity czas treningu: {(end_time_phase2 - start_time):.2f} sekund ---")

# === ZAPIS HISTORII NAUCZANIA ===
# Tworzymy folder 'history' jeśli nie istnieje
os.makedirs(os.path.dirname(HISTORY_SAVE_PATH), exist_ok=True)
np.save(HISTORY_SAVE_PATH, history)
print(f"Historia treningu zapisana do {HISTORY_SAVE_PATH}")


# === WIZUALIZACJA WYNIKÓW TRENINGU (krzywe uczenia) ===
print("\nWizualizacja krzywych uczenia...")

total_epochs = EPOCHS_PHASE1 + EPOCHS_PHASE2

plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(range(total_epochs), history['train_acc'], label='Training Accuracy')
plt.plot(range(total_epochs), history['val_acc'], label='Validation Accuracy')
plt.legend(loc='lower right')
plt.title(f'Training and Validation Accuracy ({current_model_name})')

plt.subplot(1, 2, 2)
plt.plot(range(total_epochs), history['train_loss'], label='Training Loss')
plt.plot(range(total_epochs), history['val_loss'], label='Validation Loss')
plt.legend(loc='upper right')
plt.title(f'Training and Validation Loss ({current_model_name})')
plt.savefig(PLOT_SAVE_PATH) # Zapisujemy wykres pod zmienną PLOT_SAVE_PATH
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

#wyniki val acc dla kolejnych modelów (wybrane najlepsze modele):
#Mobilenetv2: 0.7178
#Resnet50: 0.8137
#efficientnet_b2: 0.8772
#convNext_small: 0.9521

#wyniki val loss dla kolejnych modelów:
#Mobilenetv2: 0.9345
#resnet50: 0.6128
#efficient_b2: 0.3939
#convNext_small: 0.2018

#trenowanie convNext_small modelu zajęło trochę ponad półtorej godziny