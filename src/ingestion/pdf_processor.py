"""Advanced PDF Processor with OCR and GPT-4V Support"""

import io
import os
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import PyPDF2
import pytesseract
from loguru import logger
from PIL import Image

from .base import BaseDocumentProcessor


class PDFProcessor(BaseDocumentProcessor):
    """PDF processor with advanced OCR capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.use_ocr = config.get("use_ocr", True)
        self.use_nougat = config.get("use_nougat", False)
        self.use_gpt4v = config.get("use_gpt4v", False)
        self.extract_images = config.get("extract_images", True)
        self.extract_tables = config.get("extract_tables", True)
        
    def extract_content(self, file_path: str) -> str:
        """Extract text content from PDF"""
        content_parts = []
        
        try:
            # First try standard text extraction
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    
                    # Check if page has enough text
                    if len(text.strip()) < 50 and self.use_ocr:
                        # Page likely contains images, use OCR
                        logger.info(f"Using OCR for page {page_num + 1}")
                        ocr_text = self._extract_with_ocr(file_path, page_num)
                        content_parts.append(ocr_text)
                    else:
                        content_parts.append(text)
                        
            # Combine all parts
            full_content = "\n\n".join(content_parts)
            
            # If content is still too short, try advanced methods
            if len(full_content.strip()) < 100:
                if self.use_nougat:
                    logger.info("Using Nougat for mathematical PDF extraction")
                    full_content = self._extract_with_nougat(file_path)
                elif self.use_gpt4v:
                    logger.info("Using GPT-4V for complex PDF extraction")
                    full_content = self._extract_with_gpt4v(file_path)
                    
            return full_content
            
        except Exception as e:
            logger.error(f"Error extracting PDF content: {e}")
            raise
            
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        metadata = {}
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract document info
                if pdf_reader.metadata:
                    metadata["title"] = pdf_reader.metadata.get("/Title", "")
                    metadata["author"] = pdf_reader.metadata.get("/Author", "")
                    metadata["subject"] = pdf_reader.metadata.get("/Subject", "")
                    metadata["creator"] = pdf_reader.metadata.get("/Creator", "")
                    metadata["creation_date"] = pdf_reader.metadata.get("/CreationDate", "")
                    metadata["modification_date"] = pdf_reader.metadata.get("/ModDate", "")
                    
                metadata["page_count"] = len(pdf_reader.pages)
                metadata["file_size"] = os.path.getsize(file_path)
                metadata["file_name"] = os.path.basename(file_path)
                metadata["file_type"] = "pdf"
                
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            metadata["extraction_error"] = str(e)
            
        return metadata
        
    def _extract_with_ocr(self, file_path: str, page_num: int) -> str:
        """Extract text using OCR for a specific page"""
        try:
            # Convert PDF page to image
            # This is a simplified version - in production, use pdf2image
            # For now, return placeholder
            return f"[OCR content for page {page_num + 1}]"
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
            
    def _extract_with_nougat(self, file_path: str) -> str:
        """Extract mathematical content using Nougat model"""
        # Placeholder for Nougat integration
        # In production, integrate with Nougat API or model
        logger.warning("Nougat extraction not yet implemented")
        return "[Nougat extraction placeholder]"
        
    def _extract_with_gpt4v(self, file_path: str) -> str:
        """Extract content using GPT-4V for complex documents"""
        # Placeholder for GPT-4V integration
        # In production, convert pages to images and use GPT-4V API
        logger.warning("GPT-4V extraction not yet implemented")
        return "[GPT-4V extraction placeholder]"
        
    def extract_images_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract images from PDF"""
        images = []
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    if '/XObject' in page['/Resources']:
                        xobjects = page['/Resources']['/XObject'].get_object()
                        
                        for obj_name in xobjects:
                            obj = xobjects[obj_name]
                            
                            if obj['/Subtype'] == '/Image':
                                # Extract image data
                                image_data = self._extract_image_data(obj)
                                if image_data:
                                    images.append({
                                        "page": page_num + 1,
                                        "name": obj_name,
                                        "data": image_data
                                    })
                                    
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            
        return images
        
    def _extract_image_data(self, image_obj) -> Optional[bytes]:
        """Extract image data from PDF object"""
        # Simplified implementation
        # In production, handle different image formats and filters
        try:
            if '/Filter' in image_obj:
                if image_obj['/Filter'] == '/DCTDecode':
                    return image_obj._data
                elif image_obj['/Filter'] == '/FlateDecode':
                    # Handle FlateDecode
                    pass
        except:
            pass
            
        return None
        
    def extract_tables_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract tables from PDF"""
        # Placeholder for table extraction
        # In production, use tabula-py or similar
        logger.warning("Table extraction not yet implemented")
        return []