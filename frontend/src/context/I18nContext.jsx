import React, { createContext, useContext, useState, useEffect } from 'react';
import en from '../i18n/en.json';
import ta from '../i18n/ta.json';
import tanglish from '../i18n/tanglish.json';

const dictionaries = {
  en,
  ta,
  tanglish
};

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    return localStorage.getItem('kanakku_lang') || 'ta';
  });

  const setLanguage = (newLang) => {
    if (dictionaries[newLang]) {
      setLangState(newLang);
      localStorage.setItem('kanakku_lang', newLang);
    }
  };

  const t = (key) => {
    const currentDict = dictionaries[lang] || dictionaries.en;
    return currentDict[key] || dictionaries.en[key] || key;
  };

  return (
    <I18nContext.Provider value={{ lang, setLanguage, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}
