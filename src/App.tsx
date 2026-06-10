/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Upload, Dog, RefreshCw, CheckCircle2, AlertCircle, Camera, Sparkles, X, Cpu, Layers, Award, ArrowLeft, BookOpen } from 'lucide-react';
import Markdown from 'react-markdown';
import { classifyDogBreed, ClassificationResult } from './services/classifier';
import learningCurvesImg from './images/krzywe_uczenia_convnext_finetuned.png';
import i18nData from './i18n.json';

type Language = 'pl' | 'en';

const BREEDS = [
  'Chihuahua', 'Japanese Spaniel', 'Maltese Dog', 'Pekinese', 'Tzu', 'Blenheim Spaniel', 'Papillon', 'Toy Terrier', 
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
  'Standard Poodle', 'Mexican Hairless', 'Dingo', 'Dhole', 'African Hunting Dog'
];

export default function App() {
  const [lang, setLang] = useState<Language>('pl');
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

  // Current view/page state
  const [page, setPage] = useState<'home' | 'info'>('home');

  const t = (key: keyof typeof i18nData.pl): string => {
    return (i18nData[lang] as Record<string, string>)[key] || '';
  };

  const handleLanguageChange = (newLang: Language) => {
    setLang(newLang);
    if (result && result.breed) {
      fetchBreedDescription(result.breed, newLang);
    }
  };

  const handleLogoClick = () => {
    reset();
    setPage('home');
  };

  const handleGoToBreedsList = (e: React.MouseEvent) => {
    e.preventDefault();
    setPage('info');
    setTimeout(() => {
      const element = document.getElementById('recognized-breeds');
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 150);
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.type.startsWith('image/')) {
        setError(t('error_only_image'));
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

  const fetchBreedDescription = async (breedName: string, selectedLang: Language = lang) => {
    setIsGeneratingDesc(true);
    setDescError(null);
    setAiDescription(null);
    try {
      const response = await fetch("/api/description", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ breed: breedName, lang: selectedLang })
      });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || errData.detail || (selectedLang === 'en' ? "Failed to download breed description." : "Nie udało się pobrać opisu rasy."));
      }
      const data = await response.json();
      setAiDescription(data.description);
    } catch (err) {
      console.error(err);
      setDescError(err instanceof Error ? err.message : (selectedLang === 'en' ? 'Error generating breed description via Gemini.' : 'Błąd podczas generowania opisu przez Gemini.'));
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
        fetchBreedDescription(res.breed, lang);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error_unexpected'));
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
      <nav className="p-6 sticky top-0 z-10 theme-navbar shadow-sm text-white">
        <div className="max-w-4xl mx-auto flex items-center justify-between font-medium">
          <div className="flex items-center gap-2 cursor-pointer group" onClick={handleLogoClick}>
            <div className="w-10 h-10 theme-logo-wrapper rounded-xl flex items-center justify-center text-white transition-all group-hover:scale-105">
              <Dog size={24} />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white group-hover:opacity-90 transition-opacity">DogBreed AI</h1>
          </div>
          <div className="flex items-center gap-4 text-sm">
            {/* Przełącznik Języka / Language switcher */}
            <div className="flex items-center gap-1 bg-white/10 p-1 rounded-xl border border-white/10">
              <button 
                onClick={() => handleLanguageChange('pl')} 
                className={`p-1.5 px-2.5 rounded-lg flex items-center gap-1 transition-all cursor-pointer ${
                  lang === 'pl' 
                    ? 'bg-[#3dcf10] text-white shadow-sm font-bold' 
                    : 'hover:bg-white/5 text-white/70 hover:text-white'
                }`}
                title="Polska wersja"
              >
                <span className="text-sm select-none">🇵🇱</span>
                <span className="text-[10px] font-bold">PL</span>
              </button>
              <button 
                onClick={() => handleLanguageChange('en')} 
                className={`p-1.5 px-2.5 rounded-lg flex items-center gap-1 transition-all cursor-pointer ${
                  lang === 'en' 
                    ? 'bg-[#3dcf10] text-white shadow-sm font-bold' 
                    : 'hover:bg-white/5 text-white/70 hover:text-white'
                }`}
                title="English version"
              >
                <span className="text-sm select-none">🇬🇧</span>
                <span className="text-[10px] font-bold">EN</span>
              </button>
            </div>

            <button
              onClick={() => setPage(page === 'home' ? 'info' : 'home')}
              className={`hover:text-white transition-all cursor-pointer text-sm font-semibold border px-4 py-2 rounded-xl active:scale-95 ${
                page === 'info'
                  ? 'bg-white/10 border-white text-white shadow-inner font-bold'
                  : 'bg-transparent border-[#ffe3c3]/30 text-[#ffe3c3] hover:border-[#ffe3c3]/80 hover:bg-[#ffe3c3]/5'
              }`}
            >
              {t('learn_more')}
            </button>
          </div>
        </div>
      </nav>

      <AnimatePresence mode="wait">
        {page === 'home' ? (
          <motion.main
            key="home"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.25 }}
            className="max-w-4xl mx-auto mt-12 px-6"
          >
            <header className="mb-12 text-center">
              <motion.h2 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-4xl md:text-5xl font-bold tracking-tight mb-4"
              >
                {t('hero_title')}
              </motion.h2>
              <motion.p 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="text-lg theme-text-muted max-w-xl mx-auto"
              >
                {t('hero_subtitle')}
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
                        <p className="text-xl font-semibold mb-1 text-white">{t('drop_title')}</p>
                        <p className="theme-text-muted">{t('drop_subtitle')}</p>
                      </div>
                      <div className="mt-4 flex gap-8 text-xs theme-text-muted">
                        <div className="flex items-center gap-1"><Camera size={14} /> JPG, PNG</div>
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
                                {t('btn_analyzing')}
                              </>
                            ) : (
                              <>
                                <RefreshCw size={24} />
                                {t('btn_identify')}
                              </>
                            )}
                          </button>
                          <button 
                            onClick={reset} 
                            className="text-sm theme-text-muted hover:theme-text-main transition-colors underline underline-offset-4"
                          >
                            {t('btn_choose_another')}
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
                              <p className="text-xs uppercase tracking-widest theme-text-muted font-bold mb-1">{t('likely_breed')}</p>
                              <h3 className="text-4xl font-black theme-text-main leading-tight">
                                {result.breed}
                              </h3>
                            </div>
                            <div className="flex flex-col md:items-end">
                              <p className="text-xs uppercase tracking-widest theme-text-muted font-bold mb-1">{t('confidence')}</p>
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
                                {t('warning_confidence')}
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
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 bg-white text-[#3dcf10] rounded-xl flex items-center justify-center border border-gray-200/80 shadow-sm shrink-0">
                                <Sparkles size={20} />
                              </div>
                              <h4 className="text-sm font-bold uppercase tracking-wider theme-text-muted">{t('fun_facts_header')}</h4>
                            </div>

                            {isGeneratingDesc && (
                              <div className="flex flex-col items-center justify-center py-6 gap-3">
                                <RefreshCw size={20} className="animate-spin theme-accent-text" />
                                <p className="text-sm theme-text-muted animate-pulse">{t('generating_desc')}</p>
                              </div>
                            )}

                            {descError && (
                              <div className="p-4 bg-amber-50/75 text-amber-800 rounded-2xl border border-amber-100 space-y-2">
                                <div className="flex items-center gap-2 font-semibold text-sm">
                                  <AlertCircle size={16} />
                                  <span>{t('desc_unavailable')}</span>
                                </div>
                                <p className="text-xs opacity-90">{descError}</p>
                                <button
                                  onClick={() => result && fetchBreedDescription(result.breed)}
                                  className="mt-2 text-xs font-bold underline cursor-pointer hover:opacity-80 transition-opacity"
                                >
                                  {t('btn_try_again')}
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
                              {t('btn_start_over')}
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
                  <h5 className="font-bold mb-3">{t('col1_title')}</h5>
                  <p className="text-sm theme-text-muted leading-relaxed">
                    {t('col1_text')}
                  </p>
                </div>
                <div>
                  <h5 className="font-bold mb-3">{t('col2_title')}</h5>
                  <p className="text-sm theme-text-muted leading-relaxed">
                    {t('col2_text_before_btn')}<button onClick={handleGoToBreedsList} className="text-[#3dcf10] hover:text-[#058810] font-bold underline transition-colors cursor-pointer bg-transparent border-none p-0 inline">{t('learn_more')}</button>
                  </p>
                </div>
                <div>
                  <h5 className="font-bold mb-3">{t('col3_title')}</h5>
                  <p className="text-sm theme-text-muted leading-relaxed">
                    {t('col3_text')}
                  </p>
                </div>
              </div>
            </section>
          </motion.main>
        ) : (
          <motion.main
            key="info"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.25 }}
            className="max-w-4xl mx-auto mt-12 px-6"
          >
            {/* Przycisk wstecz */}
            <button
              onClick={() => setPage('home')}
              className="mb-8 flex items-center gap-2 text-sm text-[#794400] hover:opacity-85 transition-opacity font-bold cursor-pointer"
            >
              <ArrowLeft size={16} /> {t('back_to_classification')}
            </button>

            {/* Hero Sekcja w tym samym stylu */}
            <header className="mb-12 text-center">
              <span className="text-xs uppercase tracking-widest text-[#794400] bg-[#794400]/10 px-3 py-1 rounded-full font-extrabold mb-3 inline-block">
                {t('info_head_badge')}
              </span>
              <h2 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4 text-[#111827]">
                {t('info_head_title')}
              </h2>
            </header>

            {/* Bento-grid stylizowanych kart */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
              <div className="theme-card p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 bg-white text-[#3dcf10] rounded-xl flex items-center justify-center mb-4 border border-gray-200/80 shadow-sm">
                    <Cpu size={24} />
                  </div>
                  <h3 className="text-xl font-bold mb-2 text-[#111827]">{t('card1_title')}</h3>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {t('card1_text')}
                  </p>
                </div>
              </div>

              <div className="theme-card p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 bg-white text-[#3dcf10] rounded-xl flex items-center justify-center mb-4 border border-gray-200/80 shadow-sm">
                    <Layers size={24} />
                  </div>
                  <h3 className="text-xl font-bold mb-2 text-[#111827]">{t('card2_title')}</h3>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {t('card2_text')}
                  </p>
                </div>
              </div>

              <div className="theme-card p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 bg-white text-[#3dcf10] rounded-xl flex items-center justify-center mb-4 border border-gray-200/80 shadow-sm">
                    <Award size={24} />
                  </div>
                  <h3 className="text-xl font-bold mb-2 text-[#111827]">{t('card3_title')}</h3>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {t('card3_text')}
                  </p>
                </div>
              </div>

              <div className="theme-card p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 bg-white text-[#3dcf10] rounded-xl flex items-center justify-center mb-4 border border-gray-200/80 shadow-sm">
                    <Sparkles size={24} />
                  </div>
                  <h3 className="text-xl font-bold mb-2 text-[#111827]">{t('card4_title')}</h3>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {t('card4_text')}
                  </p>
                </div>
              </div>
            </div>

            {/* Duża sekcja dla użytkownika do wpisania dalszych danych */}
            <div className="theme-card p-8 rounded-3xl border border-gray-100 shadow-sm mb-12 text-left">
              <h3 className="text-2xl font-black mb-4 flex items-center gap-3 text-[#111827]">
                <div className="w-10 h-10 bg-white text-[#3dcf10] rounded-xl flex items-center justify-center border border-gray-200/80 shadow-sm shrink-0">
                  <BookOpen size={20} />
                </div>
                <span>{t('info_section_title')}</span>
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">
                {t('info_section_text1')}
              </p>

              <div className="my-6 max-w-2xl mx-auto rounded-2xl overflow-hidden border border-gray-100 shadow-sm bg-white">
                <img
                  src={learningCurvesImg}
                  alt={t('info_section_image_alt')}
                  className="w-full h-auto object-cover"
                  referrerPolicy="no-referrer"
                />
              </div>

              <p className="text-sm text-gray-600 leading-relaxed">
                {t('info_section_text2')}
              </p>

              <div className="border-t border-gray-100 pt-6 mt-6" id="recognized-breeds">
                <h4 className="text-sm font-bold text-gray-800 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Dog size={16} className="text-[#3dcf10]" />
                  <span>{t('recognized_breeds_title')}</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-1.5 text-xs text-gray-500 bg-gray-50/50 p-4 rounded-2xl border border-gray-100 max-h-72 overflow-y-auto custom-scrollbar">
                  {BREEDS.map((breed, index) => (
                    <div key={index} className="flex items-center gap-2 hover:text-[#3dcf10] transition-colors py-0.5" id={`breed-${index}`}>
                      <span className="font-mono text-[10px] text-gray-400 w-5 inline-block text-right">{index + 1}.</span>
                      <span className="font-medium text-gray-700">{breed}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.main>
        )}
      </AnimatePresence>

      <footer className="mt-20 py-8 text-center text-xs theme-text-muted tracking-widest font-bold uppercase">
        Kuchini, 2026, DogBreed AI
      </footer>
    </div>
  );
}
