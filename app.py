import streamlit as st
from openai import OpenAI
import requests
from PIL import Image, ImageStat
import io
import os

# --- Configuration ---
TEMPLATE_URL = "https://github.com/Antosser/Roblox-Shirt-Template/blob/master/template.png?raw=true"
TEMPLATE_FILENAME = "shirt_overlay.png"
ROBLOX_WIDTH = 585
ROBLOX_HEIGHT = 559

# Logo placement coordinates (center of front torso)
LOGO_X = 231
LOGO_Y = 74
LOGO_SIZE = 128

# Pattern tile size
PATTERN_SIZE = 150

# --- Helper Functions ---

def download_template():
    """Downloads the Roblox shirt template overlay."""
    if not os.path.exists(TEMPLATE_FILENAME):
        try:
            with st.spinner("Downloading Roblox shirt template..."):
                response = requests.get(TEMPLATE_URL, timeout=15)
                response.raise_for_status()
                with open(TEMPLATE_FILENAME, "wb") as f:
                    f.write(response.content)
                st.success("Template downloaded!")
        except Exception as e:
            st.error(f"Failed to download template: {e}")
            st.info("Creating a transparent placeholder template...")
            # Create a fully transparent placeholder
            placeholder = Image.new("RGBA", (ROBLOX_WIDTH, ROBLOX_HEIGHT), (0, 0, 0, 0))
            placeholder.save(TEMPLATE_FILENAME)

def get_openai_client():
    """Initializes the OpenAI client."""
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            st.error("OpenAI API Key not found in .streamlit/secrets.toml")
            st.stop()
        return OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"Error initializing OpenAI: {e}")
        st.stop()

def generate_image(client, prompt):
    """Generates an image using DALL-E 3."""
    try:
        with st.spinner("🎨 Generating with DALL-E 3..."):
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            img_url = response.data[0].url
            img_response = requests.get(img_url)
            img_response.raise_for_status()
            return Image.open(io.BytesIO(img_response.content)).convert("RGBA")
    except Exception as e:
        st.error(f"Image generation failed: {e}")
        return None

def get_average_color(image):
    """Calculates the average/dominant color of an image."""
    # Convert to RGB for stats calculation
    rgb_image = image.convert("RGB")
    stat = ImageStat.Stat(rgb_image)
    # Get average of each channel
    avg_color = tuple(int(c) for c in stat.mean[:3])
    return avg_color

def create_logo_mode_image(ai_image):
    """Creates shirt with centered logo and background matching dominant color."""
    # Resize AI image to logo size
    logo = ai_image.resize((LOGO_SIZE, LOGO_SIZE), Image.Resampling.LANCZOS)
    
    # Get average color from the logo
    avg_color = get_average_color(logo)
    
    # Create base image filled with average color
    base = Image.new("RGBA", (ROBLOX_WIDTH, ROBLOX_HEIGHT), (*avg_color, 255))
    
    # Paste logo at specified coordinates
    base.paste(logo, (LOGO_X, LOGO_Y), mask=logo)
    
    return base

def create_pattern_mode_image(ai_image):
    """Creates shirt with tiled pattern."""
    # Resize AI image to tile size
    tile = ai_image.resize((PATTERN_SIZE, PATTERN_SIZE), Image.Resampling.LANCZOS)
    
    # Create base image
    base = Image.new("RGBA", (ROBLOX_WIDTH, ROBLOX_HEIGHT))
    
    # Tile the pattern across the base
    for x in range(0, ROBLOX_WIDTH, PATTERN_SIZE):
        for y in range(0, ROBLOX_HEIGHT, PATTERN_SIZE):
            base.paste(tile, (x, y))
    
    return base

def apply_template_overlay(base_image):
    """Applies the shirt template overlay on top of the base image."""
    try:
        overlay = Image.open(TEMPLATE_FILENAME).convert("RGBA")
        
        # Ensure overlay matches dimensions
        if overlay.size != (ROBLOX_WIDTH, ROBLOX_HEIGHT):
            overlay = overlay.resize((ROBLOX_WIDTH, ROBLOX_HEIGHT), Image.Resampling.LANCZOS)
        
        # Composite: overlay on top of base (transparent areas show base through)
        final = Image.alpha_composite(base_image, overlay)
        
        return final
    except Exception as e:
        st.warning(f"Could not apply overlay: {e}")
        return base_image

# --- Main App ---

def main():
    st.set_page_config(page_title="Roblox Shirt Generator", page_icon="👕")
    
    st.title("👕 Roblox Shirt Generator")
    st.write("Generate custom Roblox shirt textures using AI!")
    
    # Setup - download template if needed
    download_template()
    
    # UI Controls
    prompt = st.text_input(
        "Describe your design:",
        placeholder="e.g., golden dragon logo, neon cyberpunk pattern"
    )
    
    mode = st.selectbox(
        "Generation Mode:",
        ["Logo Mode", "Pattern Mode"],
        help="Logo Mode: Centers a single image on the shirt. Pattern Mode: Tiles the image across the shirt."
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        generate_btn = st.button("🚀 Generate", type="primary")
    
    # Generation Logic
    if generate_btn:
        if not prompt:
            st.warning("Please enter a design description.")
            return
        
        client = get_openai_client()
        ai_image = generate_image(client, prompt)
        
        if ai_image:
            with st.spinner("Processing image..."):
                # Route based on mode
                if mode == "Logo Mode":
                    base_image = create_logo_mode_image(ai_image)
                else:
                    base_image = create_pattern_mode_image(ai_image)
                
                # Apply template overlay
                final_image = apply_template_overlay(base_image)
            
            # Display result
            st.success("✅ Shirt generated!")
            st.image(final_image, caption=f"Roblox Shirt - {mode}", use_container_width=False)
            
            # Download button
            buf = io.BytesIO()
            final_image.save(buf, format="PNG")
            st.download_button(
                label="📥 Download PNG",
                data=buf.getvalue(),
                file_name="roblox_shirt.png",
                mime="image/png"
            )

if __name__ == "__main__":
    main()
