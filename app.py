import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import time
from urllib.parse import urljoin
import re

# Page configuration
st.set_page_config(
    page_title="La Fiancee Joyas - Asistente Virtual",
    page_icon="💍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling with black text
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
    }
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 15px;
        margin: 10px 0;
        color: #000000 !important;
    }
    .stChatMessage p, .stChatMessage div, .stChatMessage span {
        color: #000000 !important;
    }
    .chat-header {
        background: linear-gradient(135deg, #d4af37 0%, #f4e5c3 100%);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        color: #333333;
    }
    .product-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #d4af37;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #000000;
    }
    .product-card h4, .product-card p, .product-card b {
        color: #000000 !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #d4af37 0%, #f4e5c3 100%);
        color: #333;
        border: none;
        border-radius: 20px;
        padding: 10px 25px;
        font-weight: bold;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .stTextInput input {
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = os.getenv('OPENAI_API_KEY', '')

# Enhanced Web Scraper Class
class LaFianceeJoyasScraper:
    def __init__(self):
        self.base_url = "https://lafianceejoyas.co"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.data = {
            'products': [],
            'categories': [],
            'company_info': {
                'name': 'La Fiancee Joyas',
                'description': 'Joyas en Oro 18k - Joyas Únicas',
                'currency': 'COP',
                'country': 'Colombia',
                'website': 'lafianceejoyas.co',
                'instagram': '@lafianceejoyas'
            }
        }
    
    def scrape_product_page(self, url):
        """Scrape detailed product information from product page"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            product = {}
            
            # Extract product title
            title_elem = soup.find('h1', class_='product-title')
            if not title_elem:
                title_elem = soup.find('h1')
            product['name'] = title_elem.text.strip() if title_elem else url.split('/')[-1].replace('-', ' ').title()
            
            # Extract price - try multiple methods
            price_elem = (
                soup.find('span', class_='money') or 
                soup.find('span', {'data-product-price': True}) or
                soup.find('span', class_='price') or
                soup.find('div', class_='product-price')
            )
            if price_elem:
                price_text = price_elem.text.strip()
                # Extract numeric value
                price_match = re.search(r'[\d,.]+', price_text.replace('.', '').replace(',', ''))
                if price_match:
                    product['price'] = f"${price_match.group()}"
            
            # Extract description
            desc_elem = (
                soup.find('div', class_='product-description') or 
                soup.find('div', {'itemprop': 'description'}) or
                soup.find('div', class_='description')
            )
            if desc_elem:
                product['description'] = desc_elem.text.strip()[:500]
            
            # Extract specifications from description or meta
            full_text = product.get('description', '') + ' ' + product['name']
            product['material'] = self.extract_material(full_text)
            product['weight'] = self.extract_weight(full_text)
            product['size'] = self.extract_size(full_text)
            product['category'] = self.categorize_product(product['name'])
            product['url'] = url
            
            return product
        except Exception as e:
            print(f"Error scraping product {url}: {e}")
            return None
    
    def scrape_homepage(self):
        """Scrape homepage and collection pages for products"""
        try:
            # Scrape main page
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all product links
            product_links = set()
            
            # Method 1: Look for product links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/products/' in href:
                    full_url = urljoin(self.base_url, href)
                    # Clean URL (remove query parameters)
                    clean_url = full_url.split('?')[0]
                    product_links.add(clean_url)
            
            # Method 2: Try collections
            collections = [
                '/collections/all', 
                '/collections/cadenas', 
                '/collections/pulseras', 
                '/collections/aretes', 
                '/collections/anillos', 
                '/collections/dijes',
                '/collections/joyas'
            ]
            
            for collection in collections:
                try:
                    col_response = requests.get(self.base_url + collection, headers=self.headers, timeout=10)
                    col_soup = BeautifulSoup(col_response.content, 'html.parser')
                    
                    for link in col_soup.find_all('a', href=True):
                        href = link.get('href', '')
                        if '/products/' in href:
                            full_url = urljoin(self.base_url, href)
                            clean_url = full_url.split('?')[0]
                            product_links.add(clean_url)
                    
                    time.sleep(0.5)  # Be polite to server
                except:
                    continue
            
            # Scrape each product page (limit to 60 for performance)
            total_links = list(product_links)[:60]
            progress_text = st.empty()
            
            for idx, url in enumerate(total_links):
                progress_text.text(f"Escaneando producto {idx + 1} de {len(total_links)}...")
                
                product_data = self.scrape_product_page(url)
                if product_data:
                    self.data['products'].append(product_data)
                
                time.sleep(0.3)  # Be polite to server
            
            progress_text.empty()
            
            # Extract unique categories
            self.data['categories'] = list(set([p['category'] for p in self.data['products'] if p.get('category')]))
            
            return len(self.data['products']) > 0
        except Exception as e:
            st.error(f"Error durante el escaneo: {e}")
            return False
    
    def categorize_product(self, name):
        """Categorize product based on name"""
        name_lower = name.lower()
        if 'cadena' in name_lower:
            return 'Cadenas'
        elif 'pulso' in name_lower or 'pulsera' in name_lower or 'brazalete' in name_lower:
            return 'Pulseras'
        elif 'topo' in name_lower or 'arete' in name_lower or 'pendiente' in name_lower:
            return 'Aretes'
        elif 'anillo' in name_lower or 'argolla' in name_lower:
            return 'Anillos'
        elif 'dije' in name_lower or 'colgante' in name_lower or 'medalla' in name_lower:
            return 'Dijes'
        return 'Joyas'
    
    def extract_material(self, text):
        """Extract material from text"""
        text_lower = text.lower()
        if 'oro amarillo' in text_lower:
            return 'Oro Amarillo 18K'
        elif 'oro blanco' in text_lower:
            return 'Oro Blanco 18K'
        elif 'oro rosa' in text_lower or 'oro rosado' in text_lower:
            return 'Oro Rosa 18K'
        elif 'tres oros' in text_lower or '3 oros' in text_lower:
            return 'Tres Oros 18K'
        elif 'oro' in text_lower:
            return 'Oro 18K'
        return 'Oro 18K'
    
    def extract_weight(self, text):
        """Extract weight from text"""
        weight_match = re.search(r'(\d+[,.]?\d*)\s*gr', text.lower())
        if weight_match:
            return weight_match.group(1) + 'gr'
        return None
    
    def extract_size(self, text):
        """Extract size/length from text"""
        size_match = re.search(r'(\d+)\s*cm', text.lower())
        if size_match:
            return size_match.group(1) + 'cm'
        # Also look for mm
        size_match = re.search(r'(\d+)\s*mm', text.lower())
        if size_match:
            return size_match.group(1) + 'mm'
        return None

# OpenAI Chat Function
def chat_with_openai(messages, api_key, knowledge_base):
    """Chat with OpenAI API with enhanced conversational abilities"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        # Create detailed product catalog from REAL scraped data
        products_info = []
        for p in knowledge_base['products']:
            product_str = f"- {p['name']}"
            if p.get('price'):
                product_str += f" - Precio: {p['price']} COP"
            if p.get('category'):
                product_str += f" - Categoría: {p['category']}"
            if p.get('material'):
                product_str += f" - Material: {p['material']}"
            if p.get('weight'):
                product_str += f" - Peso: {p['weight']}"
            if p.get('size'):
                product_str += f" - Tamaño: {p['size']}"
            if p.get('description'):
                product_str += f" - Descripción: {p['description'][:100]}"
            if p.get('url'):
                product_str += f" - URL: {p['url']}"
            products_info.append(product_str)
        
        products_catalog = "\n".join(products_info)
        
        # Enhanced system prompt for conversational AI
        system_prompt = f"""Eres un asesor experto y amigable de La Fiancee Joyas, una joyería colombiana especializada en oro 18K italiano de alta calidad.

INFORMACIÓN DE LA EMPRESA:
- Nombre: La Fiancee Joyas
- Especialidad: Joyas en Oro 18K (amarillo, blanco, rosa y tres oros)
- Productos: Cadenas, pulseras, aretes, anillos y dijes
- Moneda: Pesos colombianos (COP)
- Sitio web: lafianceejoyas.co
- Instagram: @lafianceejoyas

CATÁLOGO COMPLETO DE PRODUCTOS (EXTRAÍDO DEL SITIO WEB REAL):
{products_catalog}

CATEGORÍAS DISPONIBLES:
{', '.join(knowledge_base['categories'])}

TU ROL Y PERSONALIDAD:
- Eres un asesor experto pero cercano y conversacional
- Entiendes las ocasiones especiales (bodas, aniversarios, regalos, compromiso)
- Haces preguntas para entender mejor las necesidades del cliente
- Das recomendaciones personalizadas basadas en el presupuesto y ocasión
- Usas emojis moderadamente para ser más cálido
- Hablas de manera natural, no como un robot

CÓMO RESPONDER SEGÚN LA OCASIÓN:
1. **Para Compromiso/Boda**: Recomienda anillos elegantes del catálogo real, menciona la importancia del oro 18K para una pieza tan especial
2. **Para Regalo de Novia/Esposa**: Sugiere cadenas, pulseras o aretes del catálogo según estilo (clásico, moderno)
3. **Para Uso Diario**: Recomienda piezas versátiles y duraderas del inventario
4. **Para Ocasión Especial**: Piezas más llamativas o con diseños únicos que tengamos en stock

REGLAS CRÍTICAS:
- SOLO menciona productos que estén en el catálogo anterior
- SIEMPRE usa los precios exactos del catálogo (si están disponibles)
- Si un precio no está disponible, di "Consultar precio en lafianceejoyas.co o Instagram @lafianceejoyas"
- Incluye el link del producto cuando sea relevante
- NO inventes productos, precios o características que no estén en el catálogo
- Si el cliente pregunta por algo que no tenemos, sugiere alternativas REALES del catálogo
- Sé conversacional: "¡Qué emoción! Para un compromiso te recomendaría..." en lugar de respuestas secas

PREGUNTAS QUE PUEDES HACER:
- ¿Para qué ocasión es la joya?
- ¿Qué estilo prefiere? (clásico, moderno, minimalista)
- ¿Tienes algún presupuesto en mente?
- ¿Prefiere oro amarillo, blanco o rosa?
- ¿Es para uso diario o ocasiones especiales?

INFORMACIÓN ADICIONAL:
- Garantía: Todas las joyas son 100% oro 18K italiano con certificado
- Envíos: Sí, a toda Colombia (consultar detalles por Instagram)
- Cuidado: Evitar químicos, guardar en lugar seco, limpiar con paño suave
- Personalización: Consultar disponibilidad por Instagram @lafianceejoyas
- Tienda física: Contactar por Instagram para ubicación"""

        # Prepare messages
        api_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=api_messages,
            temperature=0.8,
            max_tokens=800
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"Lo siento, hay un problema técnico: {str(e)}. Por favor verifica tu API key de OpenAI o intenta nuevamente."

# Sidebar
with st.sidebar:
    st.markdown("""
        <div class="chat-header">
            <h1>💍 La Fiancee Joyas</h1>
            <p>Asistente Virtual de Joyas 18K</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # OpenAI API Key input
    st.subheader("🔑 Configuración")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=st.session_state.openai_api_key,
        help="Ingresa tu API key de OpenAI"
    )
    
    if api_key:
        st.session_state.openai_api_key = api_key
        st.success("✅ API Key configurada")
    else:
        st.warning("⚠️ Se requiere API Key de OpenAI")
    
    st.markdown("---")
    
    # Scraping section
    st.subheader("🌐 Datos del Sitio Web")
    
    if st.button("🔄 Escanear Sitio Web", use_container_width=True):
        with st.spinner("Escaneando lafianceejoyas.co... Esto puede tomar unos minutos..."):
            scraper = LaFianceeJoyasScraper()
            success = scraper.scrape_homepage()
            
            if success:
                st.session_state.scraped_data = scraper.data
                st.success(f"✅ {len(scraper.data['products'])} productos encontrados del sitio web real")
            else:
                st.error("❌ Error al escanear el sitio")
    
    if st.session_state.scraped_data:
        st.info(f"📦 {len(st.session_state.scraped_data['products'])} productos reales en base de datos")
        
        # Show categories
        with st.expander("📋 Categorías"):
            for cat in st.session_state.scraped_data['categories']:
                count = len([p for p in st.session_state.scraped_data['products'] if p.get('category') == cat])
                st.write(f"• {cat}: {count} productos")
        
        # Show sample products
        with st.expander("👀 Vista previa de productos"):
            for i, p in enumerate(st.session_state.scraped_data['products'][:3]):
                st.write(f"**{i+1}. {p['name']}**")
                if p.get('price'):
                    st.write(f"   💰 {p['price']}")
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("⚡ Acciones Rápidas")
    
    if st.button("💍 Anillo de compromiso", use_container_width=True):
        st.session_state.quick_message = "Quiero comprar un anillo de compromiso para mi novia"
    
    if st.button("💝 Regalo para esposa", use_container_width=True):
        st.session_state.quick_message = "Busco un regalo especial para mi esposa"
    
    if st.button("💒 Joya de boda", use_container_width=True):
        st.session_state.quick_message = "Necesito unas argollas de matrimonio"
    
    if st.button("🎁 Regalo aniversario", use_container_width=True):
        st.session_state.quick_message = "Es nuestro aniversario, quiero regalarle una joya"
    
    if st.button("🚚 Información de envíos", use_container_width=True):
        st.session_state.quick_message = "¿Hacen envíos? ¿Cuánto demora?"
    
    if st.button("💎 Garantía y calidad", use_container_width=True):
        st.session_state.quick_message = "¿Qué garantía tienen las joyas?"
    
    if st.button("🧹 Limpiar Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # Info
    st.markdown("""
        <div style="background: white; padding: 10px; border-radius: 10px; font-size: 12px; color: #000000;">
            <b>🌐 Website:</b> lafianceejoyas.co<br>
            <b>📱 Instagram:</b> @lafianceejoyas<br>
            <b>✨ Especialidad:</b> Oro 18K<br>
            <b>🇨🇴 Ubicación:</b> Colombia
        </div>
    """, unsafe_allow_html=True)

# Main content
st.markdown("""
    <div class="chat-header">
        <h1>💍 Asistente Virtual La Fiancee Joyas</h1>
        <p>Tu experto en joyas de oro 18K</p>
    </div>
""", unsafe_allow_html=True)

# Check if API key is available
if not st.session_state.openai_api_key:
    st.warning("⚠️ Por favor ingresa tu API Key de OpenAI en la barra lateral para comenzar.")
    st.stop()

# Check if data has been scraped - NO HARDCODED DATA
if not st.session_state.scraped_data:
    st.warning("⚠️ **IMPORTANTE:** Debes escanear el sitio web primero para obtener datos reales.")
    st.info("👉 Presiona el botón '🔄 Escanear Sitio Web' en la barra lateral para cargar productos, precios y detalles directamente de lafianceejoyas.co")
    st.info("⏱️ El escaneo toma 1-2 minutos y cargará todos los productos disponibles del sitio web real.")
    st.stop()

# Initialize chat with welcome message
if not st.session_state.messages:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "¡Hola! 👋 Bienvenido a La Fiancee Joyas. Soy tu asesor personal de joyas en oro 18K.\n\n¿En qué puedo ayudarte hoy? Ya sea para un compromiso, boda, aniversario o un regalo especial, estoy aquí para ayudarte a encontrar la joya perfecta. 😊\n\nTengo información actualizada de todos nuestros productos disponibles en el sitio web."
    }]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle quick messages
if 'quick_message' in st.session_state:
    user_input = st.session_state.quick_message
    del st.session_state.quick_message
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            response = chat_with_openai(
                st.session_state.messages,
                st.session_state.openai_api_key,
                st.session_state.scraped_data
            )
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# Chat input
if user_input := st.chat_input("Escribe tu mensaje aquí..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            response = chat_with_openai(
                st.session_state.messages,
                st.session_state.openai_api_key,
                st.session_state.scraped_data
            )
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# Footer with products showcase (no images, just text from REAL data)
if st.session_state.scraped_data and st.session_state.scraped_data['products']:
    st.markdown("---")
    st.subheader("✨ Productos del Catálogo Real")
    
    cols = st.columns(3)
    for idx, product in enumerate(st.session_state.scraped_data['products'][:9]):
        with cols[idx % 3]:
            product_info = f"<div class='product-card'>"
            product_info += f"<h4>💍 {product['name'][:50]}</h4>"
            if product.get('price'):
                product_info += f"<p><b>Precio:</b> {product['price']} COP</p>"
            if product.get('category'):
                product_info += f"<p><b>Categoría:</b> {product['category']}</p>"
            if product.get('material'):
                product_info += f"<p><b>Material:</b> {product['material']}</p>"
            if product.get('weight'):
                product_info += f"<p><b>Peso:</b> {product['weight']}</p>"
            if product.get('size'):
                product_info += f"<p><b>Tamaño:</b> {product['size']}</p>"
            product_info += "</div>"
            
            st.markdown(product_info, unsafe_allow_html=True)
            
            if st.button(f"Ver en sitio web", key=f"btn_{idx}"):
                st.info(f"🔗 {product.get('url', 'URL no disponible')}")