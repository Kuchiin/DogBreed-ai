import os
import matplotlib.pyplot as plt

DATA_DIR = 'projekt01/Images_of_dogs'

class_counts = {}

# Przejdź przez podfoldery (rasy)
for breed_folder in os.listdir(DATA_DIR):
    breed_path = os.path.join(DATA_DIR, breed_folder)
    if os.path.isdir(breed_path):
        # Zlicz pliki graficzne w folderze
        count = len(os.listdir(breed_path))
        
        # Wyodrębnij nazwę rasy z nazwy folderu (np. "n02085620-Chihuahua" -> "Chihuahua")
        breed_name = breed_folder.split('-')[-1].replace('_', ' ').title()
        
        class_counts[breed_name] = count

sorted_counts = sorted(class_counts.items(), key=lambda item: item[1], reverse=True)

# Wypisz wyniki
print("Rozkład zdjęć na rasy:")
for breed, count in sorted_counts:
    print(f"- {breed}: {count} zdjęć")

# Wizualizacja posortowanych wyników
if sorted_counts:
    breeds = [item[0] for item in sorted_counts]
    counts = [item[1] for item in sorted_counts]

    plt.figure(figsize=(15, 8)) # Zwiększ rozmiar dla czytelności
    plt.bar(breeds, counts)
    plt.xlabel("Rasa Psa")
    plt.ylabel("Liczba Zdjęć")
    plt.title("Rozkład Liczby Zdjęć dla Poszczególnych Ras Psów")
    plt.xticks(rotation=90, fontsize=8) # Obróć etykiety i zmniejsz czcionkę dla lepszej czytelności
    plt.tight_layout() # Dopasuj układ, aby etykiety nie zachodziły na siebie
    plt.savefig('projekt01/wykresy/counter_wykres.png')
    plt.close()