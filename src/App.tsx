/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Upload, Dog, RefreshCw, CheckCircle2, AlertCircle, Camera, Sparkles, X } from 'lucide-react';
import Markdown from 'react-markdown';
import { classifyDogBreed, ClassificationResult } from './services/classifier';

export default function App() {
  const [image, setImage] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ClassificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Gemini API description state
  const [aiDescription, setAiDescription] = useState<string | null>(null);
  const [isGeneratingDesc, setIsGeneratingDesc] = useState(false);
  const [descError, setDescError] = useState<string | null>(null);

  // Warning state for low confidence
  const [showWarning, setShowWarning] = useState(true);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.type.startsWith('image/')) {
        setError('Proszę wybrać plik graficzny.');
        return;
      }
      processFile(selectedFile);
    }
  };

  const processFile = (file: File) => {
    setFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      setImage(e.target?.result as string);
      setResult(null);
      setError(null);
    };
    reader.readAsDataURL(file);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith('image/')) {
      processFile(droppedFile);
    }
  }, []);

  const fetchBreedDescription = async (breedName: string) => {
    setIsGeneratingDesc(true);
    setDescError(null);
    setAiDescription(null);
    try {
      const response = await fetch("/api/description", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ breed: breedName })
      });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || errData.detail || "Nie udało się pobrać opisu rasy.");
      }
      const data = await response.json();
      setAiDescription(data.description);
    } catch (err) {
      console.error(err);
      setDescError(err instanceof Error ? err.message : 'Błąd podczas generowania opisu przez Gemini.');
    } finally {
      setIsGeneratingDesc(false);
    }
  };

  const analyzeBreed = async () => {
    if (!image || !file) return;

    setIsAnalyzing(true);
    setError(null);
    setAiDescription(null);
    setDescError(null);
    setShowWarning(true);
    try {
      const res = await classifyDogBreed(image);
      setResult(res);
      if (res.breed) {
        fetchBreedDescription(res.breed);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Wystąpił nieoczekiwany błąd.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const reset = () => {
    setImage(null);
    setFile(null);
    setResult(null);
    setError(null);
    setAiDescription(null);
    setDescError(null);
    setShowWarning(true);
  };

  return (
    <div className="min-h-screen font-sans theme-text-main theme-selection-bg pb-20">
      {/* Header */}
      <nav className="p-6 sticky top-0 z-10 theme-navbar shadow-sm">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={reset}>
            <div className="w-10 h-10 theme-logo-wrapper rounded-xl flex items-center justify-center text-white">
              <Dog size={24} />
            </div>
            <h1 className="text-xl font-bold tracking-tight">DogBreed AI</h1>
          </div>
          <div className="hidden sm:block text-sm theme-text-muted font-medium">
            Klasyfikacja rasy psa
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto mt-12 px-6">
        <header className="mb-12 text-center">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl md:text-5xl font-bold tracking-tight mb-4"
          >
            Sprawdź rasę swojego psa
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-lg theme-text-muted max-w-xl mx-auto"
          >
            Wgraj zdjęcie, a nasza sztuczna inteligencja zidentyfikuje rasę i poda najważniejsze cechy Twojego pupila.
          </motion.p>
        </header>

        <section className="grid grid-cols-1 lg:grid-cols-1 gap-8">
          <AnimatePresence mode="wait">
            {!image ? (
              <motion.div
                key="upload"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onDragOver={(e) => e.preventDefault()}
                onDrop={onDrop}
                className="relative group theme-upload-zone rounded-3xl p-12 text-center cursor-pointer"
              >
                <input
                  type="file"
                  onChange={handleImageUpload}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  accept="image/*"
                />
                <div className="flex flex-col items-center gap-4">
                  <div className="w-20 h-20 theme-upload-icon-wrapper rounded-full flex items-center justify-center">
                    <Upload size={32} className="transition-colors" />
                  </div>
                  <div>
                    <p className="text-xl font-semibold mb-1">Upuść zdjęcie tutaj</p>
                    <p className="theme-text-muted">lub kliknij, aby wybrać plik z komputera</p>
                  </div>
                  <div className="mt-4 flex gap-8 text-xs theme-text-muted">
                    <div className="flex items-center gap-1"><Camera size={14} /> JPG, PNG</div>
                    <div className="flex items-center gap-1"><CheckCircle2 size={14} /> Wysoka dokładność</div>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="preview"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="rounded-3xl overflow-hidden theme-card shadow-sm"
              >
                <div className="aspect-video relative bg-black flex items-center justify-center">
                  <img src={image} alt="Upload preview" className="max-h-full max-w-full object-contain" />
                  {!result && !isAnalyzing && (
                    <button 
                      onClick={reset}
                      className="absolute top-4 right-4 p-2 bg-black/50 hover:bg-black/70 text-white rounded-full backdrop-blur-md transition-colors"
                    >
                      <RefreshCw size={20} />
                    </button>
                  )}
                </div>

                <div className="p-8">
                  {error && (
                    <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl flex items-center gap-3 border border-red-100">
                      <AlertCircle size={20} />
                      <p className="text-sm font-medium">{error}</p>
                    </div>
                  )}

                  {!result ? (
                    <div className="flex flex-col items-center gap-4">
                      <button
                        disabled={isAnalyzing}
                        onClick={analyzeBreed}
                        className="w-full py-4 theme-btn-primary disabled:opacity-50 text-white font-bold rounded-2xl flex items-center justify-center gap-2 text-lg"
                      >
                        {isAnalyzing ? (
                          <>
                            <RefreshCw size={24} className="animate-spin" />
                            Analizowanie zdjęcia...
                          </>
                        ) : (
                          <>
                            <RefreshCw size={24} />
                            Rozpoznaj rasę
                          </>
                        )}
                      </button>
                      <button 
                        onClick={reset} 
                        className="text-sm theme-text-muted hover:theme-text-main transition-colors underline underline-offset-4"
                      >
                        Wybierz inne zdjęcie
                      </button>
                    </div>
                  ) : (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="space-y-8"
                    >
                      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b theme-border pb-6">
                        <div>
                          <p className="text-xs uppercase tracking-widest theme-text-muted font-bold mb-1">Prawdopodobna Rasa</p>
                          <h3 className="text-4xl font-black theme-text-main leading-tight">
                            {result.breed}
                          </h3>
                        </div>
                        <div className="flex flex-col md:items-end">
                          <p className="text-xs uppercase tracking-widest theme-text-muted font-bold mb-1">Confidence</p>
                          <div className="flex items-center gap-2">
                             <div className="text-3xl font-mono theme-accent-text font-bold">
                               {result.confidence}%
                             </div>
                             <div className="w-16 h-2 theme-progress-track rounded-full overflow-hidden">
                               <motion.div 
                                 initial={{ width: 0 }}
                                 animate={{ width: `${result.confidence}%` }}
                                 className="h-full theme-accent-bg"
                               />
                             </div>
                          </div>
                        </div>
                      </div>

                      {result.confidence < 75 && showWarning && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.95 }}
                          className="p-5 bg-red-50 border border-red-100 text-red-800 rounded-2xl flex items-start gap-3.5 relative overflow-hidden"
                        >
                          <AlertCircle className="text-red-500 shrink-0 mt-0.5" size={20} />
                          <div className="text-sm leading-relaxed pr-8 font-medium">
                            Uwaga, confidence level spadł poniżej 75%, może to oznaczać że nasz model błędnie zaklasyfikował twojego pupila, wskazując inną, podobną wizualnie rasę.
                          </div>
                          <button
                            onClick={() => setShowWarning(false)}
                            className="absolute top-4 right-4 text-red-400 hover:text-red-700 transition-colors cursor-pointer"
                            aria-label="Zamknij"
                          >
                            <X size={18} />
                          </button>
                        </motion.div>
                      )}

                      {/* Pole z opisem rasy za pomocą Gemini API */}
                      <div className="py-2 border-b theme-border space-y-4">
                        <div className="flex items-center gap-2">
                          <Sparkles size={18} className="theme-accent-text" />
                          <h4 className="text-sm font-bold uppercase tracking-wider theme-text-muted">Ciekawostki i Opis Rasy (Gemini AI)</h4>
                        </div>

                        {isGeneratingDesc && (
                          <div className="flex flex-col items-center justify-center py-6 gap-3">
                            <RefreshCw size={20} className="animate-spin theme-accent-text" />
                            <p className="text-sm theme-text-muted animate-pulse">Generowanie opisu rasy przez sztuczną inteligencję...</p>
                          </div>
                        )}

                        {descError && (
                          <div className="p-4 bg-amber-50/75 text-amber-800 rounded-2xl border border-amber-100 space-y-2">
                            <div className="flex items-center gap-2 font-semibold text-sm">
                              <AlertCircle size={16} />
                              <span>Opis rasy jest tymczasowo niedostępny</span>
                            </div>
                            <p className="text-xs opacity-90">{descError}</p>
                            <button
                              onClick={() => result && fetchBreedDescription(result.breed)}
                              className="mt-2 text-xs font-bold underline cursor-pointer hover:opacity-80 transition-opacity"
                            >
                              Spróbuj ponownie
                            </button>
                          </div>
                        )}

                        {aiDescription && (
                          <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3 }}
                            className="bg-gray-50/50 p-5 rounded-2xl border theme-border theme-text-main text-sm leading-relaxed"
                          >
                            <div className="markdown-body">
                              <Markdown>{aiDescription}</Markdown>
                            </div>
                          </motion.div>
                        )}
                      </div>

                      <div className="pt-4">
                        <button
                          onClick={reset}
                          className="w-full py-4 theme-btn-secondary font-bold rounded-2xl flex items-center justify-center gap-2"
                        >
                          Zacznij od nowa
                        </button>
                      </div>
                    </motion.div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Info Footer */}
        <section className="mt-20 border-t theme-border pt-12 pb-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center md:text-left">
            <div>
              <h5 className="font-bold mb-3">Jak to działa?</h5>
              <p className="text-sm theme-text-muted leading-relaxed">
                Nasz system wykorzystuje zaawansowany model splotowy (ConvNext) trenowany na ponad 20.000 zdjęć psów, aby zapewnić najwyższą precyzję rozpoznawania.
              </p>
            </div>
            <div>
              <h5 className="font-bold mb-3">120 Ras</h5>
              <p className="text-sm theme-text-muted leading-relaxed">
                Nasz model jest w stanie rozpoznać 120 różnych ras psów, od popularnych po te bardziej egzotyczne. Jeżeli rasy twojego psa nie ma w naszej bazie,
                model wskaże rasę którą uzna za najbardziej podobną, a wskaźnik confidence odpowiednio się obniży.
              </p>
            </div>
            <div>
              <h5 className="font-bold mb-3">Prywatność</h5>
              <p className="text-sm theme-text-muted leading-relaxed">
                Twoje zdjęcia są przesyłane bezpiecznie i wykorzystywane wyłącznie do celów klasyfikacji. Nie przechowujemy Twoich prywatnych danych.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="mt-20 py-8 text-center text-xs theme-text-muted tracking-widest font-bold uppercase">
        Wojciech Nowak, 2026, DogBreed AI
      </footer>
    </div>
  );
}
