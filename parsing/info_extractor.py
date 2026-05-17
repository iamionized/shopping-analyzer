import re
from typing import Dict, Any
from bs4 import BeautifulSoup

def extract_basic_receipt_info_from_html(
    soup: BeautifulSoup, receipt_id: str, receipt_date: str, store: str
) -> Dict[str, Any]:
    receipt_data = {
        "id": receipt_id,
        "purchase_date": receipt_date,
        "total_price": None,
        "total_price_no_saving": None,
        "saved_amount": None,
        "sticker_discount_amount": None,
        "sticker_discount_pct": [],
        "saved_pfand": None,
        "lidlplus_saved_amount": None,
        "store": store,
        "items": [],
    }

    # 1. Total Price Check
    try:
        purchase_summary_elements = soup.find_all(id=re.compile(r"^purchase_summary_"))
        for element in purchase_summary_elements:
            element_text = element.get_text().strip().lower()
            if "zu zahlen" in element_text or "totaal" in element_text or "te betalen" in element_text:
                amount_spans = element.parent.find_all("span", class_=re.compile(r"css_bold|css_big"))
                for span in amount_spans:
                    span_text = span.get_text().strip()
                    if re.match(r"^\d+,\d+$", span_text):
                        receipt_data["total_price"] = span_text
                        break
                if receipt_data["total_price"]:
                    break
    except:
        pass

    # 2. Extract savings via stateful parsing (Solves the newline issue!)
    try:
        total_regular_savings = 0.0
        total_lidlplus_savings = 0.0
        purchase_list = soup.find("span", class_="purchase_list")
        if purchase_list:
            lines = purchase_list.get_text().split("\n")
            context_keyword = None
            
            for line in lines:
                line_lower = line.strip().lower()
                
                # Determine what kind of discount we are looking at and save it to context
                if "lidl plus" in line_lower or "kassabon korting" in line_lower:
                    context_keyword = "lidl_plus"
                elif any(kw in line_lower for kw in ["preisvorteil", "in prijs verlaagd", "actieprijs", "2 voor actie"]):
                    context_keyword = "regular"
                elif ("rabatt" in line_lower or "korting" in line_lower) and not any(x in line_lower for x in ["totaal", "gesamter"]):
                    if context_keyword != "lidl_plus": 
                        context_keyword = "regular_sticker"
                        pct_match = re.search(r"(\d{1,3})\s*%", line_lower)
                        if pct_match:
                            receipt_data.setdefault("sticker_discount_pct", []).append(int(pct_match.group(1)))

                # Check if the current line has a negative amount
                amount_match = re.search(r"-\s*(\d+[\.,]\d{2})", line.strip())
                if amount_match:
                    val = float(amount_match.group(1).replace(",", "."))
                    
                    # Apply the amount to whatever context we are currently in
                    if context_keyword == "lidl_plus":
                        total_lidlplus_savings += val
                    elif context_keyword in ["regular", "regular_sticker"]:
                        total_regular_savings += val
                        if context_keyword == "regular_sticker":
                            if receipt_data.get("sticker_discount_amount") is None:
                                receipt_data["sticker_discount_amount"] = 0.0
                            receipt_data["sticker_discount_amount"] += val
                    
                    # Reset context so we don't accidentally apply the discount to a future negative number
                    context_keyword = None

        if total_regular_savings > 0:
            receipt_data["saved_amount"] = f"{total_regular_savings:.2f}".replace(".", ",")
        if total_lidlplus_savings > 0:
            receipt_data["lidlplus_saved_amount"] = f"{total_lidlplus_savings:.2f}".replace(".", ",")
            
    except:
        pass

    # 3. Fallback for German Lidl Plus (EUR gespart block)
    if not receipt_data.get("lidlplus_saved_amount"):
        try:
            vat_info_elements = soup.find_all("span", class_="vat_info")
            for element in vat_info_elements:
                if "eur gespart" in element.get_text().lower():
                    amount_match = re.search(r"(\d+,\d+)\s+EUR", element.get_text())
                    if amount_match:
                        receipt_data["lidlplus_saved_amount"] = amount_match.group(1)
                        break
        except:
            pass

    return receipt_data
