import os
import torch
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from PIL import Image # Do ładowania obrazów
import numpy as np
import matplotlib.pyplot as plt

# Wyciszanie logów (niezmienne dla PyTorch, ale można zostawić)
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Parametry obrazu
IMG_HEIGHT = 300
IMG_WIDTH = 300
BATCH_SIZE = 32

# Proporcje podziału
TRAIN_RATIO = 0.7
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Ustalenie urządzenia do obliczeń (GPU jeśli dostępne, w przeciwnym razie CPU)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Używane urządzenie: {DEVICE}")

class DogDataset(Dataset):
    def __init__(self, image_paths, labels, class_to_idx, transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.class_to_idx = class_to_idx
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        image = Image.open(img_path).convert('RGB') # Ładowanie obrazu PIL

        label_raw = self.labels[idx]
        label_idx = self.class_to_idx[label_raw]
        label = torch.tensor(label_idx, dtype=torch.long) # Etykieta jako tensor Long

        if self.transform:
            image = self.transform(image)

        return image, label

def get_class_info(data_dir):
    all_image_labels_raw = []
    for breed_folder in os.listdir(data_dir):
        breed_path = os.path.join(data_dir, breed_folder)
        if os.path.isdir(breed_path):
            breed_label = breed_folder
            for image_file in os.listdir(breed_path):
                if image_file.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    all_image_labels_raw.append(breed_label)
    
    unique_labels_raw = sorted(list(set(all_image_labels_raw)))
    class_names_full = [label.split('-')[-1].replace('_', ' ').title() for label in unique_labels_raw]
    class_to_idx = {label: i for i, label in enumerate(unique_labels_raw)}
    return class_names_full, class_to_idx

def load_and_preprocess_data(data_dir):
    """
    Ładuje dane obrazowe z podanej ścieżki, dzieli je na zbiory treningowy, walidacyjny i testowy,
    oraz stosuje preprocessing i augmentację dla PyTorch.

    Args:
        data_dir (str): Ścieżka do głównego folderu z rasami psów.

    Returns:
        tuple: (train_loader, val_loader, test_loader, num_classes, class_names, class_to_idx)
    """
    
    # --- Krok 1: Zbieranie ścieżek i etykiet ---
    all_image_paths = []
    all_image_labels_raw = []

    print("Zbieranie ścieżek do zdjęć i etykiet...")
    for breed_folder in os.listdir(data_dir):
        breed_path = os.path.join(data_dir, breed_folder)
        if os.path.isdir(breed_path):
            breed_label = breed_folder
            for image_file in os.listdir(breed_path):
                if image_file.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    all_image_paths.append(os.path.join(breed_path, image_file))
                    all_image_labels_raw.append(breed_label)

    num_total_images = len(all_image_paths)
    print(f"Znaleziono {num_total_images} wszystkich zdjęć.")

    # --- Krok 2: Mapowanie nazw ras na indeksy ---
    unique_labels_raw = sorted(list(set(all_image_labels_raw)))
    num_classes = len(unique_labels_raw)
    class_to_idx = {label: i for i, label in enumerate(unique_labels_raw)}
    idx_to_class = {i: label for i, label in enumerate(unique_labels_raw)} # Do późniejszego mapowania

    class_names = [label.split('-')[-1].replace('_', ' ').title() for label in unique_labels_raw]
    
    print(f"Znaleziono {num_classes} unikalnych ras.")

    # --- Krok 3: Podział na zbiory treningowy, walidacyjny i testowy za pomocą train_test_split ---
    X_train, X_temp, y_train, y_temp = train_test_split(
        all_image_paths, all_image_labels_raw,
        test_size=(VAL_RATIO + TEST_RATIO),
        stratify=all_image_labels_raw,
        random_state=42
    )

    test_size_relative_to_temp = TEST_RATIO / (VAL_RATIO + TEST_RATIO)

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp,
        test_size=test_size_relative_to_temp,
        stratify=y_temp,
        random_state=42
    )

    print(f"Podział zakończony: Treningowych: {len(X_train)}, Walidacyjnych: {len(X_val)}, Testowych: {len(X_test)}")

    # --- Krok 4: Definicja transformacji (preprocessing + augmentacja) ---
    # MobileNetV2 oczekuje obrazów znormalizowanych do średniej [0.485, 0.456, 0.406] i std [0.229, 0.224, 0.225]
    # To jest standardowa normalizacja dla ImageNet
    
    # Uwaga: torchvision.transforms wykonuje central_crop trochę inaczej
    # Jeśli chcesz zachować dokładne zachowanie z TensorFlow (kwadrat z krótszego boku),
    # możesz najpierw zastosować transforms.Resize(min(H, W)), a potem transforms.CenterCrop(min(H, W))
    # Ale dla prostoty i standardu, zaczniemy od Resize i CenterCrop.

    train_transforms = transforms.Compose([
        transforms.Resize(min(IMG_HEIGHT, IMG_WIDTH)),
        transforms.CenterCrop(min(IMG_HEIGHT,IMG_WIDTH)),
        transforms.Resize((IMG_HEIGHT, IMG_WIDTH)), # Zmiana rozmiaru
        transforms.RandomHorizontalFlip(),         # Losowe odbicie poziome
        transforms.RandomRotation(15),             # Losowy obrót o +/- 15 stopni
        transforms.ColorJitter(brightness=0.1, contrast=0.1), # Losowa zmiana jasności/kontrastu
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)), # Dodane losowe przesunięcia
        transforms.ToTensor(),                     # Konwersja obrazu PIL na tensor PyTorch (0-1)
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_test_transforms = transforms.Compose([
        transforms.Resize((IMG_HEIGHT, IMG_WIDTH)), # Zmiana rozmiaru
        transforms.CenterCrop(IMG_HEIGHT),
        transforms.ToTensor(),                     # Konwersja obrazu PIL na tensor PyTorch (0-1)
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]) # Normalizacja ImageNet
    ])

    # --- Krok 5: Tworzenie instancji Dataset i DataLoader ---
    train_dataset = DogDataset(X_train, y_train, class_to_idx, transform=train_transforms)
    val_dataset = DogDataset(X_val, y_val, class_to_idx, transform=val_test_transforms)
    test_dataset = DogDataset(X_test, y_test, class_to_idx, transform=val_test_transforms)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=os.cpu_count() // 2, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=os.cpu_count() // 2, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=os.cpu_count() // 2, pin_memory=True)

    print(f"Liczba zdjęć w zbiorze treningowym: {len(train_dataset)}")
    print(f"Liczba zdjęć w zbiorze walidacyjnym: {len(val_dataset)}")
    print(f"Liczba zdjęć w zbiorze testowym: {len(test_dataset)}")
    
    # --- Wizualizacja przykładów po augmentacji ---
    print("\n--- Wizualizacja przykładowych zdjęć po augmentacji (PyTorch) ---")
    plt.figure(figsize=(10, 10))
    # Funkcja do denormalizacji obrazu dla wyświetlania
    inv_normalize = transforms.Normalize(
        mean=[-0.485/0.229, -0.456/0.224, -0.406/0.225],
        std=[1/0.229, 1/0.224, 1/0.225]
    )

    for images, labels in train_loader:
        for i in range(min(9, BATCH_SIZE)):
            ax = plt.subplot(3, 3, i + 1)
            # Przenieś obraz na CPU, odłącz od grafu, przekształć na numpy
            img = inv_normalize(images[i]).permute(1, 2, 0).cpu().numpy()
            img = np.clip(img, 0, 1) # Przytnij wartości do [0,1] na wypadek błędów normalizacji
            plt.imshow(img)
            plt.title(class_names[labels[i].item()]) # .item() aby pobrać wartość skalarną z tensora
            plt.axis("off")
        break # Weź tylko jedną partię
    plt.tight_layout()
    plt.savefig('projekt01/wykresy/preprocessing_pytorch_wykres.png')
    plt.close()

    return train_loader, val_loader, test_loader, num_classes, class_names, class_to_idx

# Jeśli ten plik jest uruchamiany bezpośrednio
if __name__ == '__main__':
    DATA_DIR = 'projekt01/Images_of_dogs' # Ścieżka tylko do testowania
    train_loader, val_loader, test_loader, num_classes, class_names, class_to_idx = load_and_preprocess_data(DATA_DIR)
    print("\nPreprocessing danych PyTorch zakończony. DataLoadery są gotowe.")
    
    # Przykładowe pobranie jednej partii danych
    for i, (images, labels) in enumerate(train_loader):
        print(f"Partia {i+1}: Kształt obrazów: {images.shape}, Kształt etykiet: {labels.shape}")
        print(f"Typ danych obrazów: {images.dtype}, Typ danych etykiet: {labels.dtype}")
        break
    class_names_for_backend, _ = get_class_info(DATA_DIR)
    print(class_names_for_backend) # Możesz to skopiować