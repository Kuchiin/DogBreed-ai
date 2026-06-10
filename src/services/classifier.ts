export interface ClassificationResult {
  breed: string;
  confidence: number;
  description: string;
  characteristics: string[];
}

export async function classifyDogBreed(imageWithPrefix: string): Promise<ClassificationResult> {
  const response = await fetch("/api/classify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: imageWithPrefix })
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || "Wystąpił błąd podczas klasyfikacji.");
  }

  return await response.json();
}
