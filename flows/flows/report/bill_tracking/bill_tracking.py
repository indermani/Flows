# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	columns, data = get_columns(filters), get_date(filters)
	return columns, data


def get_columns(filters):
	return [
		"Indent Date:Date:100",
		"Indent:Link/Indent:100",
		"Customer::250",
		"Bill Date:Date:100",
		"Bill No.::100",
		"Bill Receive Date:Date:100"
	]


def get_date(filters):
	# return frappe.db.sql("""
	# SELECT indent.posting_date, indent.name, indent_item.customer, indent_invoice.transaction_date,
	# indent_invoice.invoice_number, ifnull(indent_invoice.invoice_receive_date, '')
	# FROM `tabIndent Item` indent_item, `tabIndent` indent, `tabIndent Invoice` indent_invoice
	# WHERE indent_item.parent = indent.name
	# AND indent_item.name = indent_invoice.indent_item
	# AND indent_invoice.docstatus != 2
	# AND indent.posting_date BETWEEN '{from_date}' AND '{to_date}'
	# ORDER BY indent.posting_date DESC;
	# """.format(**filters))

	invoice_map = {}
	rows = []

	indent_items = get_indents_items(filters)
	invoices = get_invoices(filters)

	for i in invoices:
		invoice_map[i.indent_item] = i

	for i in indent_items:
		row = [
			i.posting_date,
			i.indent_name,
			i.customer
		]

		if i.name in invoice_map:
			invoice = invoice_map[i.name]
			row.extend([
				invoice.transaction_date,
				invoice.invoice_number,
				invoice.invoice_receive_date
			])
		else:
			row.extend([''] * 3)

		rows.append(row)

	return rows


def get_indents_items(filters):
	return frappe.db.sql("""
	SELECT indent_item.name, indent.posting_date, indent.name AS indent_name, indent_item.customer
	FROM `tabIndent Item` indent_item, `tabIndent` indent
	WHERE indent_item.parent = indent.name
	AND indent.posting_date BETWEEN '{from_date}' AND '{to_date}'
	ORDER BY indent.posting_date DESC, indent_item.customer
	""".format(**filters), as_dict=True)


def get_invoices(filters):
	return frappe.db.sql("""
	SELECT * FROM `tabIndent Invoice`
	WHERE indent_item IN (
		SELECT indent_item.name
		FROM `tabIndent Item` indent_item, `tabIndent` indent
		WHERE indent_item.parent = indent.name
		AND indent.posting_date BETWEEN '{from_date}' AND '{to_date}'
		ORDER BY indent.posting_date DESC, indent_item.customer
	)
	""".format(**filters), as_dict=True)