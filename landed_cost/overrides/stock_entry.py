
import frappe
import erpnext
from frappe import _

from frappe.utils import (
	cint,
	cstr,
	flt,
)
# from erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher import LandedCostVoucher
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.stock_ledger import (
		validate_cancellation,
		set_as_cancel,
		get_args_for_future_sle,
		validate_serial_no,
		get_incoming_outgoing_rate_for_cancel,
		make_entry,
		get_combine_datetime,
		get_or_make_bin,
		repost_current_voucher,
		update_bin_qty	
	)

from erpnext.controllers.taxes_and_totals import init_landed_taxes_and_totals
#  inested of above 
# class init_landed_taxes_and_totals:
# 	def __init__(self, doc):
# 		self.doc = doc
# 		self.tax_field = "taxes" if self.doc.doctype == "Landed Cost Voucher" else "additional_costs"
# 		self.set_account_currency()
# 		self.set_exchange_rate()
# 		self.set_amounts_in_company_currency()

# 	def set_account_currency(self):
# 		company_currency = erpnext.get_company_currency(self.doc.company)
# 		for d in self.doc.get(self.tax_field):
# 			if not d.account_currency:
# 				account_currency = frappe.get_cached_value("Account", d.expense_account, "account_currency")
# 				d.account_currency = account_currency or company_currency

# 	def set_exchange_rate(self):
# 		company_currency = erpnext.get_company_currency(self.doc.company)
# 		for d in self.doc.get(self.tax_field):
# 			if d.account_currency == company_currency:
# 				d.exchange_rate = 1
# 			elif not d.exchange_rate:
# 				d.exchange_rate = get_exchange_rate(
# 					self.doc.posting_date,
# 					account=d.expense_account,
# 					account_currency=d.account_currency,
# 					company=self.doc.company,
# 				)

# 			if not d.exchange_rate:
# 				frappe.throw(_("Row {0}: Exchange Rate is mandatory").format(d.idx))

# 	def set_amounts_in_company_currency(self):
# 		for d in self.doc.get(self.tax_field):
# 			d.amount = flt(d.amount, d.precision("amount"))
# 			d.base_amount = flt(d.amount * flt(d.exchange_rate), d.precision("base_amount"))



class NegativeStockError(frappe.ValidationError):
	pass

class CustomStockEntry(StockEntry):
	def on_update_after_submit(self):

		fields_to_check = [
			"total_additional_costs"
		]
		child_tables = {
			"additional_costs": ("expense_account", "amount"),
			"items": ("additional_cost"),
		}
		doc_before_update = self.get_doc_before_save()

		self.needs_repost = False

		if len(doc_before_update.get("additional_costs")) != len(self.get("additional_costs")):
			self.needs_repost = True
		if not self.needs_repost:
			self.needs_repost = self.check_if_fields_updated(fields_to_check, child_tables)

		if self.needs_repost:
			# self.validate_for_repost()
			self.db_set("repost_required", self.needs_repost)
			# self.repost_stock_entries()
	
	@frappe.whitelist()
	def repost_stock_entries(self):
		if self.repost_required:
			repost_ledger = frappe.new_doc("Repost Stock Ledger")
			repost_ledger.company = self.company
			repost_ledger.append("vouchers", {"voucher_type": self.doctype, "voucher_no": self.name})
			repost_ledger.flags.ignore_permissions = True
			repost_ledger.insert()
			repost_ledger.submit()
			self.db_set("repost_required", 0)
		else:
			frappe.throw(_("No updates pending for reposting"))

	# override methods just for repost stock entries
	def calculate_rate_and_amount_on_repost(self, reset_outgoing_rate=True, raise_error_if_no_rate=True):
		self.set_basic_rate(reset_outgoing_rate, raise_error_if_no_rate)
		init_landed_taxes_and_totals(self)
		self.distribute_additional_costs()

		self.update_valuation_rate()
		self.set_total_incoming_outgoing_value()
		self.set_total_amount()

		if not reset_outgoing_rate:
			self.set_serial_and_batch_bundle()
		
		self.db_update()
		

	
	# def calculate_total_additional_costs_for_repost(self):
	# 	if self.additional_costs:
	# 		total = [d.base_amount for d in self.additional_costs ]
	# 		self.total_additional_costs = flt(total, self.precision("total_additional_costs"))
