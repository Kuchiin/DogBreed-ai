export interface ClassificationResult {
  breed: string;
  confidence: number;
  description: string;
  characteristics: string[];
}

export async function classifyDogBreed(imageWithPrefix: string): Promise<ClassificationResult> {
  const apiUrl = import.meta.env.VITE_API_URL;
  const isCustomUrl = !!apiUrl;
  
  // Jeśli jest zdefiniowany zewnętrzny URL, odpytujemy bezpośrednio endpoint /predict serwera FastAPI
  const url = isCustomUrl 
    ? `${apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl}/predict`
    : "/api/classify";

  console.log("Wysyłanie zapytania do:", url);

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: imageWithPrefix })
  });

  const responseText = await response.text();

  if (!response.ok) {
    let errorMessage = `Wystąpił błąd podczas klasyfikacji (Status: ${response.status}).`;
    try {
      const errorData = JSON.parse(responseText);
      errorMessage = errorData.error || errorData.detail || errorMessage;
    } catch (e) {
      if (responseText.includes("<!DOCTYPE") || responseText.includes("<html")) {
        errorMessage = `Adres URL API prawdopodobnie zwraca stronę HTML zamiast JSON. Upewnij się, że używasz bezpośredniego adresu Spaces, np. https://kuchiin-dog-breed-classifier-backend.hf.space (zamiast https://huggingface.co/spaces/...)`;
      } else if (responseText.trim()) {
        errorMessage = `Błąd serwera (status ${response.status}): ${responseText.slice(0, 150)}`;
      }
    }
    throw new Error(errorMessage);
  }

  let data: any;
  try {
    data = JSON.parse(responseText);
  } catch (err) {
    console.error("Błąd podczas parsowania JSON. Otrzymana odpowiedź:", responseText);
    if (!responseText.trim()) {
      throw new Error("Serwer zwrócił całkowicie pustą odpowiedź (pusty body). Sprawdź w logach Hugging Face Space czy aplikacja nie zgłasza błędów (np. Out of Memory lub błąd wejścia).");
    }
    if (responseText.includes("<!DOCTYPE") || responseText.includes("<html")) {
      throw new Error("Serwer zamiast JSON zwrócił stronę HTML. Upewnij się, że używasz bezpośredniego adresu '.hf.space' (np. https://kuchiin-dog-breed-classifier-backend.hf.space), a nie adresu strony Hugging Face.");
    }
    throw new Error(`Niepoprawny format odpowiedzi serwera (nie jest to poprawny JSON). Początek odpowiedzi: "${responseText.slice(0, 100)}..."`);
  }
  
  // Jeśli odpytujemy bezpośredni FastAPI, mapujemy odpowiedź do oczekiwanego formatu w aplikacji
  if (isCustomUrl) {
    return {
      breed: data.breed || "Nieznana",
      confidence: typeof data.confidence === 'number' ? data.confidence : 0,
      description: "Opis wyłączony (używasz tylko własnego modelu klasyfikacji).",
      characteristics: ["Własny model", "ConvNext Small"]
    };
  }
  
  return data;
}
