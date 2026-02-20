import json
import os
from typing import List, Dict, Any, Optional
import logging
import shutil
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = "data"
BACKUP_DIR = "data/backups"

class JSONDB:
    def __init__(self):
        # Создаем папки, если их нет
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        # Создаем файлы, если их нет
        self._ensure_file_exists("categories.json", [])
        self._ensure_file_exists("subcategories.json", [])
        self._ensure_file_exists("materials.json", [])
        self._ensure_file_exists("faq.json", [])
        self._ensure_file_exists("tips.json", [])
    
    def _ensure_file_exists(self, filename: str, default_data: list):
        """Создает файл с дефолтными данными, если его нет"""
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Создан файл {filename}")
    
    def _read_file(self, filename: str) -> List[Dict]:
        """Читает JSON файл"""
        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Файл {filename} не найден")
            return []
        except json.JSONDecodeError:
            logger.error(f"Ошибка парсинга {filename}")
            return []
        except Exception as e:
            logger.error(f"Ошибка чтения {filename}: {e}")
            return []
    
    def _write_file(self, filename: str, data: List[Dict]) -> bool:
        """Записывает JSON файл с созданием бэкапа"""
        filepath = os.path.join(DATA_DIR, filename)
        backup_path = os.path.join(BACKUP_DIR, f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        
        try:
            # Создаем бэкап
            if os.path.exists(filepath):
                shutil.copy2(filepath, backup_path)
            
            # Записываем новые данные
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка записи {filename}: {e}")
            return False
    
    # ===== КАТЕГОРИИ =====
    def get_categories(self) -> List[Dict]:
        """Получить все категории"""
        return self._read_file("categories.json")
    
    def get_category(self, category_id: int) -> Optional[Dict]:
        """Получить категорию по ID"""
        categories = self.get_categories()
        for cat in categories:
            if cat['id'] == category_id:
                return cat
        return None
    
    def add_category(self, name: str) -> Dict:
        """Добавить категорию"""
        categories = self.get_categories()
        new_id = max([c['id'] for c in categories], default=0) + 1
        new_category = {
            "id": new_id,
            "name": name
        }
        categories.append(new_category)
        self._write_file("categories.json", categories)
        logger.info(f"Добавлена категория: {name} (ID: {new_id})")
        return new_category
    
    def update_category(self, category_id: int, name: str) -> bool:
        """Обновить категорию"""
        categories = self.get_categories()
        for cat in categories:
            if cat['id'] == category_id:
                cat['name'] = name
                self._write_file("categories.json", categories)
                logger.info(f"Обновлена категория ID {category_id}: {name}")
                return True
        return False
    
    def delete_category(self, category_id: int) -> bool:
        """Удалить категорию и все связанные подкатегории"""
        categories = self.get_categories()
        
        # Проверяем, есть ли категория
        category_exists = any(c['id'] == category_id for c in categories)
        if not category_exists:
            return False
        
        # Удаляем связанные подкатегории
        self.delete_subcategories_by_category(category_id)
        
        # Удаляем категорию
        categories = [c for c in categories if c['id'] != category_id]
        self._write_file("categories.json", categories)
        logger.info(f"Удалена категория ID {category_id}")
        return True
    
    # ===== ПОДКАТЕГОРИИ =====
    def get_subcategories(self, category_id: Optional[int] = None) -> List[Dict]:
        """Получить подкатегории (все или по категории)"""
        subcats = self._read_file("subcategories.json")
        if category_id:
            return [s for s in subcats if s['category_id'] == category_id]
        return subcats
    
    def get_subcategory(self, subcategory_id: int) -> Optional[Dict]:
        """Получить подкатегорию по ID"""
        subcats = self.get_subcategories()
        for sub in subcats:
            if sub['id'] == subcategory_id:
                return sub
        return None
    
    def add_subcategory(self, category_id: int, name: str, wiki_text: Optional[str] = None, 
                        pros: Optional[str] = None, cons: Optional[str] = None) -> Dict:
        """Добавить подкатегорию"""
        subcats = self.get_subcategories()
        new_id = max([s['id'] for s in subcats], default=0) + 1
        new_subcat = {
            "id": new_id,
            "category_id": category_id,
            "name": name,
            "wiki_text": wiki_text,
            "pros": pros,
            "cons": cons
        }
        subcats.append(new_subcat)
        self._write_file("subcategories.json", subcats)
        logger.info(f"Добавлена подкатегория: {name} (ID: {new_id}) к категории {category_id}")
        return new_subcat
    
    def update_subcategory(self, subcategory_id: int, **kwargs) -> bool:
        """Обновить подкатегорию"""
        subcats = self.get_subcategories()
        for sub in subcats:
            if sub['id'] == subcategory_id:
                sub.update(kwargs)
                self._write_file("subcategories.json", subcats)
                logger.info(f"Обновлена подкатегория ID {subcategory_id}")
                return True
        return False
    
    def delete_subcategory(self, subcategory_id: int) -> bool:
        """Удалить подкатегорию"""
        subcats = self.get_subcategories()
        
        # Проверяем, есть ли подкатегория
        sub_exists = any(s['id'] == subcategory_id for s in subcats)
        if not sub_exists:
            return False
        
        # Удаляем связанные материалы
        self.delete_materials_by_subcategory(subcategory_id)
        
        # Удаляем подкатегорию
        subcats = [s for s in subcats if s['id'] != subcategory_id]
        self._write_file("subcategories.json", subcats)
        logger.info(f"Удалена подкатегория ID {subcategory_id}")
        return True
    
    def delete_subcategories_by_category(self, category_id: int) -> bool:
        """Удалить все подкатегории категории"""
        subcats = self.get_subcategories()
        
        # Удаляем материалы для каждой подкатегории
        for sub in subcats:
            if sub['category_id'] == category_id:
                self.delete_materials_by_subcategory(sub['id'])
        
        # Удаляем подкатегории
        subcats = [s for s in subcats if s['category_id'] != category_id]
        self._write_file("subcategories.json", subcats)
        logger.info(f"Удалены подкатегории категории {category_id}")
        return True
    
    # ===== МАТЕРИАЛЫ =====
    def get_materials(self, subcategory_id: Optional[int] = None) -> List[Dict]:
        """Получить материалы (все или по подкатегории)"""
        materials = self._read_file("materials.json")
        if subcategory_id:
            return [m for m in materials if m['subcategory_id'] == subcategory_id]
        return materials
    
    def get_material(self, material_id: int) -> Optional[Dict]:
        """Получить материал по ID"""
        materials = self.get_materials()
        for m in materials:
            if m['id'] == material_id:
                return m
        return None
    
    def add_material(self, subcategory_id: int, order_num: int, name: str, 
                     description: Optional[str], content_type: str, content: Dict) -> Dict:
        """Добавить материал"""
        materials = self.get_materials()
        new_id = max([m['id'] for m in materials], default=0) + 1
        new_material = {
            "id": new_id,
            "subcategory_id": subcategory_id,
            "order_num": order_num,
            "name": name,
            "description": description,
            "content_type": content_type,
            "content": content
        }
        materials.append(new_material)
        
        # Сортируем по order_num
        materials.sort(key=lambda x: x['order_num'])
        
        self._write_file("materials.json", materials)
        logger.info(f"Добавлен материал: {name} (ID: {new_id})")
        return new_material
    
    def update_material(self, material_id: int, **kwargs) -> bool:
        """Обновить материал"""
        materials = self.get_materials()
        for m in materials:
            if m['id'] == material_id:
                m.update(kwargs)
                self._write_file("materials.json", materials)
                logger.info(f"Обновлен материал ID {material_id}")
                return True
        return False
    
    def delete_material(self, material_id: int) -> bool:
        """Удалить материал"""
        materials = self.get_materials()
        
        # Проверяем, есть ли материал
        material_exists = any(m['id'] == material_id for m in materials)
        if not material_exists:
            return False
        
        materials = [m for m in materials if m['id'] != material_id]
        self._write_file("materials.json", materials)
        logger.info(f"Удален материал ID {material_id}")
        return True
    
    def delete_materials_by_subcategory(self, subcategory_id: int) -> bool:
        """Удалить все материалы подкатегории"""
        materials = self.get_materials()
        materials = [m for m in materials if m['subcategory_id'] != subcategory_id]
        self._write_file("materials.json", materials)
        logger.info(f"Удалены материалы подкатегории {subcategory_id}")
        return True
    
    def get_max_order(self, subcategory_id: int) -> int:
        """Получить максимальный порядковый номер"""
        materials = self.get_materials(subcategory_id)
        if not materials:
            return 0
        return max(m['order_num'] for m in materials)
    
    # ===== FAQ =====
    def get_faq(self) -> List[Dict]:
        """Получить все FAQ"""
        return self._read_file("faq.json")
    
    def add_faq(self, question: str, answer: str) -> Dict:
        """Добавить FAQ"""
        faqs = self.get_faq()
        new_id = max([f['id'] for f in faqs], default=0) + 1
        new_faq = {
            "id": new_id,
            "question": question,
            "answer": answer
        }
        faqs.append(new_faq)
        self._write_file("faq.json", faqs)
        return new_faq
    
    def delete_faq(self, faq_id: int) -> bool:
        """Удалить FAQ"""
        faqs = self.get_faq()
        faqs = [f for f in faqs if f['id'] != faq_id]
        self._write_file("faq.json", faqs)
        return True
    
    # ===== TIPS =====
    def get_tips(self) -> List[str]:
        """Получить все советы"""
        return self._read_file("tips.json")
    
    def get_random_tip(self) -> str:
        """Получить случайный совет"""
        tips = self.get_tips()
        if not tips:
            return "💡 Учитесь каждый день!"
        import random
        return random.choice(tips)
    
    def add_tip(self, tip: str) -> bool:
        """Добавить совет"""
        tips = self.get_tips()
        tips.append(tip)
        self._write_file("tips.json", tips)
        return True
    
    def delete_tip(self, index: int) -> bool:
        """Удалить совет по индексу"""
        tips = self.get_tips()
        if 0 <= index < len(tips):
            tips.pop(index)
            self._write_file("tips.json", tips)
            return True
        return False

# Глобальный экземпляр
json_db = JSONDB()