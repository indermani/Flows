# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from flows.stdlogger import root


def execute(filters=None):
	return get_columns(filters), get_data(filters)


def get_columns(filters):
	return [
		"Customer:Link/Customer:250",
		"SAP:Data:",
		"Date:Date:",
		"Bill No.:Data:",
		"Bill Amount:Currency:",
		"Qty 19Kg:Int:",
		"Qty 35Kg:Int:",
		"Qty 47.5Kg:Int:",
		"Total KGS:Float:",
		"Discount Passed:Currency:",
		"Incentive to be passed:Currency:",
		"Credit Note to be given in customer A/c:Currency:",
		"Total Amount of Credit Note:Currency:",
		"Total Amount of Incentive:Currency:",
		"II:Link/Indent Invoice:",
	]


def get_data(filters):
	invoices = get_invoices(filters)
	rows = []

	for invoice in invoices:
		policy_name = frappe.db.get_value("Customer Plant Variables", invoice.customer_plant_variables, "omc_policy")
		policy = get_policy(policy_name)
		rs = policy.execute(invoice.name)

		c_factor = get_conversion_factor_item(invoice.item)

		rows.append([
			invoice.customer,
			invoice.customer_code,
			invoice.transaction_date,
			invoice.invoice_number,
			invoice.actual_amount,
			invoice.qty if 'FC19' in invoice.item else "",
			invoice.qty if 'FC35' in invoice.item else "",
			invoice.qty if 'FC47.5' in invoice.item else "",
			c_factor * invoice.qty,
			rs['total_discount_passed'],
			rs['incentive'],
			rs['additional_discount'],
			rs['additional_discount'] * c_factor * invoice.qty,
			rs['incentive'] * c_factor * invoice.qty,
			invoice.name
		])

	return rows


def get_invoices(filters):

	cond = ' and r.field_officer = "{}"'.format(filters.field_officer) \
	if filters.field_officer else ''

	return frappe.db.sql("""
	Select i.*, r.customer_code from `tabIndent Invoice` i
	left join `tabOMC Customer Registration` r
	on i.omc_customer_registration = r.name
	where i.docstatus = 1
	and i.supplier like 'bpcl%'
	and i.item != 'FCBK'
	and i.transaction_date between "{from_date}" and "{to_date}"
	{cond}
	order by i.customer, i.transaction_date asc
	""".format(cond=cond, **filters), as_dict=True)


def get_conversion_factor_item(item):
	return flt(item.replace('FC', '').replace('L', '').replace('EC', ''))


policies = {}
def get_policy(policy):
	if policy not in policies:
		p_obj = frappe.get_doc("OMC Policies", policy)
		p_obj.init()
		policies[policy] = p_obj
	return policies[policy]