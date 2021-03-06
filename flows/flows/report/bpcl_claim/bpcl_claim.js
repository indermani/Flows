// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.query_reports["BPCL Claim"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label":__("From Date"),
			"fieldtype":"Date",
			"width":"80",
			"default":frappe.datetime.month_start(),
			"reqd":1
		},
		{
			"fieldname":"to_date",
			"label":__("To Date"),
			"fieldtype":"Date",
			"width":"80",
			"default":frappe.datetime.month_end(),
			"reqd":1
		}
	]
};
