import streamlit as st
import cv2
import numpy as np
import os
from tempfile import NamedTemporaryFile

# Printer-specific configurations
PRINTERS = {
    "Epson Workforce C5290": {
        "INK_USAGE_PER_M2": {"Cyan": 55.29, "Magenta": 55.29, "Yellow": 55.29, "Black (K)": 55.29},
        "DEFAULT_INK_PRICES": {"Cyan": 1.0, "Magenta": 1.0, "Yellow": 1.0, "Black (K)": 1.0},
    },
    "Xerox VersaLink C405": {
        "INK_USAGE_PER_M2": {"Cyan": 0.332, "Magenta": 0.332, "Yellow": 0.332, "Black (K)": 0.332},
        "DEFAULT_INK_PRICES": {"Cyan": 331.75, "Magenta": 331.75, "Yellow": 331.75, "Black (K)": 331.75},
    },
}

DEFAULT_PAPER_COST = 2.8  # PHP per sheet
DEFAULT_MARKUP = 0.3  # 30% profit margin

# Streamlit UI
st.title("Ink Coverage & Print Cost Calculator")
st.write("Upload an image to calculate CMYK ink coverage and print cost.")

# Printer selection
printer_choice = st.selectbox("Select Printer", list(PRINTERS.keys()))
printer_config = PRINTERS[printer_choice]

# User inputs
paper_cost = st.number_input("Paper Cost (₱ per sheet)", min_value=0.0, value=DEFAULT_PAPER_COST)
markup = st.slider("Profit Margin (%)", min_value=0, max_value=500, value=int(DEFAULT_MARKUP * 100)) / 100

print_width_in = st.number_input("Print Width (inches)", min_value=0.1, value=8.27)  # Default A4 width
print_height_in = st.number_input("Print Height (inches)", min_value=0.1, value=11.69)  # Default A4 height

# Editable ink prices
ink_prices = {}
st.subheader("Ink Cost per mL (₱) or per toner unit")
for color in printer_config["DEFAULT_INK_PRICES"]:
    ink_prices[color] = st.number_input(f"{color}", min_value=0.0, value=printer_config["DEFAULT_INK_PRICES"][color])

# Convert inches to mm
PRINT_WIDTH = print_width_in * 25.4
PRINT_HEIGHT = print_height_in * 25.4

uploaded_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg", "tiff", "bmp"])

def calculate_cmyk_coverage(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return None

    # Convert BGR to CMYK approximation
    bgr = image.astype(np.float32) / 255
    K = 1 - np.max(bgr, axis=2)
    C = (1 - bgr[..., 2] - K) / (1 - K + 1e-10)
    M = (1 - bgr[..., 1] - K) / (1 - K + 1e-10)
    Y = (1 - bgr[..., 0] - K) / (1 - K + 1e-10)

    # Compute coverage for each channel
    def ink_percentage(channel):
        return round(np.mean(channel[channel > 0]) * 100, 2)  # Ignore pure white areas

    return {
        "Cyan": f"{ink_percentage(C)}%",
        "Magenta": f"{ink_percentage(M)}%",
        "Yellow": f"{ink_percentage(Y)}%",
        "Black (K)": f"{round(np.mean(K) * 100, 2)}%"
    }

def calculate_print_cost(print_width, print_height, ink_coverage, ink_usage_per_m2):
    print_area = (print_width / 1000) * (print_height / 1000)  # mm to meters
    total_ink_cost = sum(
        ((float(ink_coverage[color].strip('%')) / 100) * print_area * ink_usage_per_m2[color]) * ink_prices[color]
        for color in ink_prices
    )
    total_cost = total_ink_cost + paper_cost
    final_price = total_cost * (1 + markup)  # Apply markup
    return {
        "Ink Cost": f"₱{round(total_ink_cost, 2)}",
        "Paper Cost": f"₱{paper_cost}",
        "Total Cost": f"₱{round(total_cost, 2)}",
        "Final Price (with Markup)": f"₱{round(final_price, 2)}"
    }

if uploaded_file:
    with NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
        temp_file.write(uploaded_file.getvalue())
        temp_filename = temp_file.name

    # Display uploaded image
    st.image(temp_filename, caption="Uploaded Image", use_container_width=True)

    # Process image
    cmyk_coverage = calculate_cmyk_coverage(temp_filename)
    if cmyk_coverage:
        st.subheader("CMYK Ink Coverage")
        for color, coverage in cmyk_coverage.items():
            st.write(f"**{color}:** {coverage}")

        # Calculate cost
        pricing = calculate_print_cost(PRINT_WIDTH, PRINT_HEIGHT, cmyk_coverage, printer_config["INK_USAGE_PER_M2"])
        st.subheader("Cost Calculation")
        for item, cost in pricing.items():
            st.write(f"**{item}:** {cost}")
    else:
        st.error("Error processing the image. Please try another file.")