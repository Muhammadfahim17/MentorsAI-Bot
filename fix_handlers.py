import os
import re

def fix_handlers():
    handlers_dir = "handlers"
    for filename in os.listdir(handlers_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            filepath = os.path.join(handlers_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = re.sub(
                r'async with get_db\(\) as (\w+)',
                r'async for \1 in get_db()',
                content
            )
            
            lines = new_content.split("\n")
            for i, line in enumerate(lines):
                if "async for db in get_db()" in line:
                    indent = len(line) - len(line.lstrip())
                    if i+1 < len(lines) and lines[i+1].strip() and not lines[i+1].strip().startswith("break"):
                        pass
            
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"✅ Исправлен {filename}")

if __name__ == "__main__":
    fix_handlers()
    print("Готово! Теперь запустите бота заново.")