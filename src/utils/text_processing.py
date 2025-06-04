"""Text processing utilities"""

import re
from typing import List, Optional, Set

import spacy
from loguru import logger


class TextProcessor:
    """Utilities for text processing and analysis"""
    
    def __init__(self, spacy_model: str = "en_core_web_sm"):
        self.nlp = self._load_spacy_model(spacy_model)
        
    def _load_spacy_model(self, model_name: str):
        """Load spaCy model"""
        try:
            return spacy.load(model_name)
        except OSError:
            logger.warning(f"spaCy model {model_name} not found, downloading...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", model_name])
            return spacy.load(model_name)
            
    def extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text"""
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
    def extract_entities(self, text: str) -> List[dict]:
        """Extract named entities from text"""
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
            
        return entities
        
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """Extract keywords from text using TF-IDF"""
        doc = self.nlp(text)
        
        # Extract noun phrases and named entities
        keywords = set()
        
        # Add named entities
        for ent in doc.ents:
            if len(ent.text) > 2:
                keywords.add(ent.text.lower())
                
        # Add noun chunks
        for chunk in doc.noun_chunks:
            if len(chunk.text) > 2:
                keywords.add(chunk.text.lower())
                
        # Add important individual tokens
        for token in doc:
            if (token.pos_ in ["NOUN", "PROPN"] and 
                not token.is_stop and 
                len(token.text) > 2):
                keywords.add(token.text.lower())
                
        # Sort by frequency and return top_k
        keyword_list = list(keywords)
        return keyword_list[:top_k]
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excess whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:\'\"-]', ' ', text)
        
        # Normalize quotes
        text = re.sub(r'[""]', '"', text)
        text = re.sub(r'['']', "'", text)
        
        return text.strip()
        
    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split by double newline or common paragraph indicators
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean and filter
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if len(para) > 10:  # Minimum paragraph length
                cleaned_paragraphs.append(para)
                
        return cleaned_paragraphs
        
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using spaCy"""
        doc1 = self.nlp(text1)
        doc2 = self.nlp(text2)
        
        # Use spaCy's built-in similarity
        return doc1.similarity(doc2)
        
    def extract_noun_phrases(self, text: str) -> List[str]:
        """Extract noun phrases from text"""
        doc = self.nlp(text)
        noun_phrases = []
        
        for chunk in doc.noun_chunks:
            # Filter out very short phrases
            if len(chunk.text) > 2:
                noun_phrases.append(chunk.text)
                
        return noun_phrases
        
    def extract_relationships(self, text: str) -> List[dict]:
        """Extract subject-verb-object relationships"""
        doc = self.nlp(text)
        relationships = []
        
        for sent in doc.sents:
            # Find verbs
            for token in sent:
                if token.pos_ == "VERB":
                    # Find subject
                    subject = None
                    for child in token.children:
                        if child.dep_ == "nsubj":
                            subject = child.text
                            break
                            
                    # Find object
                    obj = None
                    for child in token.children:
                        if child.dep_ in ["dobj", "pobj"]:
                            obj = child.text
                            break
                            
                    if subject and obj:
                        relationships.append({
                            "subject": subject,
                            "verb": token.text,
                            "object": obj,
                            "sentence": sent.text
                        })
                        
        return relationships
        
    def tokenize(self, text: str, remove_stop: bool = True) -> List[str]:
        """Tokenize text"""
        doc = self.nlp(text)
        
        if remove_stop:
            tokens = [token.text.lower() for token in doc 
                     if not token.is_stop and not token.is_punct and token.text.strip()]
        else:
            tokens = [token.text.lower() for token in doc 
                     if not token.is_punct and token.text.strip()]
                     
        return tokens
        
    def get_pos_tags(self, text: str) -> List[tuple]:
        """Get part-of-speech tags"""
        doc = self.nlp(text)
        return [(token.text, token.pos_) for token in doc]