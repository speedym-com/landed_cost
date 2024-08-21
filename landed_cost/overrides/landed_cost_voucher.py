
import frappe
from frappe import _

from erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher import LandedCostVoucher

class LandedCostVoucherCustom(LandedCostVoucher):
    pass


def create_purchase_invoice_from_landed_cost(doc, method):

    remarks = ""
    cost_center = ""
    project = ""
    doctype = ""
    # Retrieve the latest purchase invoice from the purchase_receipts table
    for purchase in doc.purchase_receipts:
        purchase_name = purchase.receipt_document
        doctype = purchase.receipt_document_type
        
    purchase = frappe.get_list(
        doctype,
        filters={"docstatus": 1, "name": purchase_name},
        fields=["name", "cost_center", "project"],
        order_by="modified desc",
        limit=1
    )
    
    
    if purchase:
        cost_center = purchase[0].cost_center
        project = purchase[0].project
    
    for item in doc.items:
        remarks += item.description + ":> "+ str(item.applicable_charges) + "|| "

    for tax in doc.taxes:
        if tax.custom_purchase_invoice:
            return
        purchase_invoice = create_purchase_invoice(tax, cost_center, project)
        remarks += tax.description + "| " 
        try:
            purchase_invoice.remarks = remarks
            purchase_invoice.insert()
            purchase_invoice.submit()
            # tax.purchase_invoice = purchase_invoice.name
            tax.db_set('custom_purchase_invoice', purchase_invoice.name, update_modified=False)
            # return purchase_invoice.name
        except frappe.exceptions.ValidationError as e:
            error_message = "Error creating purchase invoice for supplier {0}: {1}".format(tax.custom_supplier, str(e))
            frappe.throw(error_message)

def create_purchase_invoice(tax, cost_center, project):
    """
    Create a new purchase invoice for a specific tax.

    Args:
        tax (frappe.model.document.Document): The tax associated with the purchase invoice.
        cost_center (str): The cost center to be set in the purchase invoice.
        project (str): The project to be set in the purchase invoice.

    Returns:
        frappe.model.document.Document: The created purchase invoice.
    """
    purchase_invoice = frappe.new_doc("Purchase Invoice")
    purchase_invoice.supplier = tax.custom_supplier
    purchase_invoice.cost_center = cost_center
    purchase_invoice.project = project
    
    purchase_invoice.currency = tax.account_currency
    purchase_invoice.conversion_rate = tax.exchange_rate
    
    purchase_invoice.append("items", {
        "item_code": tax.custom_item_code,
        "qty": 1,
        "rate": tax.amount,
        "expense_account": tax.expense_account,
        "project":project
        # Add other item details as required
    })
    return purchase_invoice

