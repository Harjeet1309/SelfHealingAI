#!/usr/bin/env python3
"""
Convert Markdown to Word Document
Requires: python-docx
Install: pip install python-docx
"""

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    print("❌ python-docx not installed")
    print("Installing python-docx...")
    import subprocess
    subprocess.check_call(["pip", "install", "python-docx"])
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

import re

def convert_markdown_to_docx(md_file, docx_file):
    """Convert markdown file to Word document"""
    
    print(f"📄 Reading {md_file}...")
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("📝 Creating Word document...")
    doc = Document()
    
    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    # Process each line
    lines = content.split('\n')
    in_code_block = False
    code_lines = []
    
    for line in lines:
        # Handle code blocks
        if line.startswith('```'):
            if in_code_block:
                # End of code block - add all code lines
                if code_lines:
                    code_text = '\n'.join(code_lines)
                    p = doc.add_paragraph(code_text)
                    p.style = 'Normal'
                    for run in p.runs:
                        run.font.name = 'Courier New'
                        run.font.size = Pt(9)
                    code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue
        
        if in_code_block:
            code_lines.append(line)
            continue
        
        # Main heading (# )
        if line.startswith('# ') and not line.startswith('## '):
            text = line[2:].strip()
            p = doc.add_heading(text, level=1)
            p.runs[0].font.color.rgb = RGBColor(0, 0, 255)
        
        # Sub heading (## )
        elif line.startswith('## ') and not line.startswith('### '):
            text = line[3:].strip()
            p = doc.add_heading(text, level=2)
            p.runs[0].font.color.rgb = RGBColor(0, 0, 128)
        
        # Sub-sub heading (### )
        elif line.startswith('### ') and not line.startswith('#### '):
            text = line[4:].strip()
            p = doc.add_heading(text, level=3)
            p.runs[0].font.color.rgb = RGBColor(64, 64, 64)
        
        # Sub-sub-sub heading (#### )
        elif line.startswith('#### '):
            text = line[5:].strip()
            p = doc.add_heading(text, level=4)
        
        # Bullet points
        elif line.startswith('- ') or line.startswith('* '):
            text = line[2:].strip()
            # Remove markdown formatting
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
            text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
            text = re.sub(r'`(.*?)`', r'\1', text)        # Code
            doc.add_paragraph(text, style='List Bullet')
        
        # Numbered lists
        elif re.match(r'^\d+\. ', line):
            text = re.sub(r'^\d+\. ', '', line).strip()
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
            text = re.sub(r'\*(.*?)\*', r'\1', text)
            text = re.sub(r'`(.*?)`', r'\1', text)
            doc.add_paragraph(text, style='List Number')
        
        # Horizontal rule
        elif line.strip() == '---':
            doc.add_paragraph('_' * 50)
        
        # Empty line
        elif not line.strip():
            doc.add_paragraph()
        
        # Regular paragraph
        else:
            if line.strip():
                # Remove markdown formatting
                text = re.sub(r'\*\*(.*?)\*\*', r'\1', line)  # Bold
                text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
                text = re.sub(r'`(.*?)`', r'\1', text)        # Code
                doc.add_paragraph(text)
    
    print(f"💾 Saving {docx_file}...")
    doc.save(docx_file)
    print(f"✅ Successfully created {docx_file}")
    print(f"\n📂 Location: {docx_file}")

if __name__ == "__main__":
    md_file = "PROJECT_COMPLETE_EXPLANATION.md"
    docx_file = "PROJECT_COMPLETE_EXPLANATION.docx"
    
    try:
        convert_markdown_to_docx(md_file, docx_file)
        print("\n✅ Conversion complete!")
        print("You can now open the .docx file in Microsoft Word")
        
        # Ask to open
        import os
        if os.name == 'nt':  # Windows
            response = input("\nOpen the document now? (y/n): ")
            if response.lower() == 'y':
                os.startfile(docx_file)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
