import re
from typing import Dict, Any
from bs4 import BeautifulSoup

from .info_extractor import extract_basic_receipt_info_from_html
from .items_extractor import extract_receipt_items_from_html

def parse_receipt_html(
    html_content: str, receipt_id: str, receipt_date: str, total_amount: float, store: str
) -> Dict[str, Any]:
    soup = BeautifulSoup(html_content, "html.parser")
    receipt_data = extract_basic_receipt_info_from_html(soup, receipt_id, receipt_date, store)
    receipt_data["items"] = extract_receipt_items_from_html(soup)

    total_savings = 0.0

    if receipt_data.get("saved_amount"):
        try:
            total_savings += float(receipt_data["saved_amount"].replace(",", "."))
        except (ValueError, AttributeError):
            pass

    if receipt_data.get("lidlplus_saved_amount"):
        try:
            total_savings += float(receipt_data["lidlplus_saved_amount"].replace(",", "."))
        except (ValueError, AttributeError):
            pass

    # BUG FIX 1: We DO NOT add sticker_discount_amount here anymore, 
    # because our new info_extractor.py already includes sticker amounts in "saved_amount".
    
    # Extract Pfand (Emballage / Statiegeld)
    pfand_savings = 0.0
    try:
        purchase_list = soup.find("span", class_="purchase_list")
        if purchase_list:
            purchase_text = purchase_list.get_text()
            pfand_matches = re.findall(
                r"(?:Pfandrückgabe|Emballage|Statiegeld|Leeggoed)\s*(-?\d+,\d+)", purchase_text, re.IGNORECASE
            )
            for match in pfand_matches:
                try:
                    pfand_val = float(match.replace(",", "."))
                    pfand_savings += abs(pfand_val) 
                except (ValueError, AttributeError):
                    pass
    except:
        pass

    if pfand_savings > 0:
        receipt_data["saved_pfand"] = f"{pfand_savings:.2f}".replace(".", ",")
        total_savings += pfand_savings

    # BUG FIX 2: Stop calculating the total from the items list! 
    # If the items_extractor misses a duplicate item, it ruins the math.
    # Instead, trust the scraped total or the API total.
    actual_total = 0.0
    if receipt_data.get("total_price"):
        try:
            actual_total = float(receipt_data["total_price"].replace(",", "."))
        except:
            actual_total = float(total_amount)
    else:
        actual_total = float(total_amount)
        if actual_total > 0:
            receipt_data["total_price"] = f"{actual_total:.2f}".replace(".", ",")

    # The true gross price (no savings) is simply what you paid + what you saved.
    if actual_total > 0:
        true_no_saving = actual_total + total_savings
        receipt_data["total_price_no_saving"] = f"{true_no_saving:.2f}".replace(".", ",")

    return receipt_data
