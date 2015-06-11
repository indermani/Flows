from summary import get_data as get_raw_data, get_warehouse_list
import frappe
from flows.flows.report.gr_summary.gr_summary import item_totals_map, get_total_rows, get_grand_totals_rows
from flows.jinja_filters import report_build_erv_item_map
from flows.stdlogger import root
items = ['FC19', 'FC35', 'FC47.5', 'FC47.5L', 'EC19', 'EC35', 'EC47.5', 'EC47.5L']


def get_data(date, warehouse):
	raw_data = get_raw_data(date, warehouse)

	filters = frappe._dict({'date': date, 'warehouse': warehouse})
	op_cl_stock_entries_aggr = init_opening_closings_map(filters)

	gr_totals = item_totals_map()
	gr_rows = compute_grs(raw_data, gr_totals)

	pr_totals = {}
	pr_rows = compute_prs(raw_data, pr_totals)

	erv_in_totals = {}
	erv_in_rows = compute_in_erv(raw_data, erv_in_totals)

	erv_out_totals = {}
	erv_out_rows = compute_out_erv(raw_data, erv_in_totals)

	gatepass_in_totals = {}
	gatepass_in_rows = compute_gatepass_in(raw_data, gatepass_in_totals)

	op_cl_map = {
	'FC19': {
	'Opening': op_cl_stock_entries_aggr['op']['FC19'],
	'ERV Rec.': erv_in_totals['FC19'] if 'FC19' in erv_in_totals else 0,
	'GR Sale': gr_totals['delivered']['FC19'],
	'PR Sale': 0,
	'GR Rec.': 0,
	'Closing': 0
	},
	'EC19': {
	'Opening': op_cl_stock_entries_aggr['op']['EC19'],
	'GR Sale': gr_totals['received']['EC19'],
	'PR Sale': 0,
	'GR Out': 0,
	'ERV Out': erv_out_totals['EC19'] if 'EC19' in erv_out_totals else 0,
	'Closing': 0
	}
	}

	compute_closings(op_cl_map)

	raw_data['op_cl_map'] = op_cl_map
	raw_data['gr_rows'] = gr_rows
	raw_data['pr_rows'] = pr_rows
	raw_data['erv_in_rows'] = erv_in_rows
	raw_data['erv_out_rows'] = erv_out_rows


	return raw_data


def init_opening_closings_map(filters):
	warehouse_list, warehouse_list_srt = get_warehouse_list(filters.warehouse)
	op_list = frappe.db.sql(
		"""
		SELECT item_code, sum(actual_qty) AS actual_qty
		FROM `tabStock Ledger Entry`
		WHERE warehouse IN ({warehouse_list_srt})
		AND posting_date < "{date}" GROUP BY item_code;
		""".format(warehouse_list_srt=warehouse_list_srt, **filters), as_dict=True
	)

	cl_list = frappe.db.sql(
		"""
		SELECT item_code, sum(actual_qty) AS actual_qty
		FROM `tabStock Ledger Entry`
		WHERE warehouse IN ({warehouse_list_srt})
		AND posting_date <= "{date}" GROUP BY item_code;
		""".format(warehouse_list_srt=warehouse_list_srt, **filters), as_dict=True
	)

	op_map = {x.item_code: x.actual_qty for x in op_list}
	cl_map = {x.item_code: x.actual_qty for x in cl_list}

	return {
	'op': op_map,
	'cl': cl_map
	}


def compute_closings(op_cl_map):
	map_instance = op_cl_map['FC19']
	map_instance['Closing'] = map_instance['Opening'] + map_instance['ERV Rec.'] + map_instance['GR Rec.'] - \
							  map_instance['GR Sale'] - map_instance['PR Sale']

	map_instance = op_cl_map['EC19']
	map_instance['Closing'] = map_instance['Opening'] - map_instance['ERV Out'] - map_instance['GR Out'] + \
							  map_instance['GR Sale'] + map_instance['PR Sale']


def compute_grs(raw_data, gr_totals):
	rows = []

	warehouse_wise_gr = {}
	sr = 0
	for gr_no, gr_value in raw_data['gr_map'].items():
		sr += 1
		warehouse_wise_gr.setdefault(gr_value.voucher.warehouse, item_totals_map())

		if gr_value['item_delivered'] and gr_value['delivered_quantity']:
			d_map = warehouse_wise_gr[gr_value.voucher.warehouse]['delivered']
			d_map.setdefault(gr_value['item_delivered'], 0)
			d_map[gr_value['item_delivered']] += gr_value['delivered_quantity']
		if gr_value['item_received'] and gr_value['received_quantity']:
			r_map = warehouse_wise_gr[gr_value.voucher.warehouse]['received']
			r_map.setdefault(gr_value['item_received'], 0)
			r_map[gr_value['item_received']] += gr_value['received_quantity']

		rows.append([
			sr,
			gr_value.voucher.name,
			gr_value.voucher.customer,
			gr_value['item_delivered'],
			gr_value['delivered_quantity'],
			gr_value['item_received'],
			gr_value['received_quantity'],
			gr_value.voucher.warehouse
		])

	rows.extend(get_total_rows(warehouse_wise_gr))
	rows.extend(get_grand_totals_rows(warehouse_wise_gr, gr_totals))

	return rows


def compute_prs(raw_data, pr_total):
	rows = []
	pr_total.update({'r': {'FC19': 0}, 'd': {'FC19': 0}})

	sr = 0
	for pr_no, pr_value in raw_data['pr_map'].items():
		sr += 1

		rows.append([
			sr,
			pr_value.voucher.name,
			pr_value.voucher.stock_owner,
			pr_value.item,
			pr_value.d_qty,
			pr_value.r_qty,
		])

		pr_total['d'][pr_value.item] += pr_value.d_qty
		pr_total['r'][pr_value.item] += pr_value.r_qty

	rows.append([
		'',
		'',
		'Grand Total',
		'',
		pr_total['d']['FC19'],
		pr_total['r']['FC19']
	])

	return rows


def compute_in_erv(raw_data, erv_total):
	return compute_erv(raw_data['erv_in_map'], erv_total)

def compute_out_erv(raw_data, erv_total):
	return compute_erv(raw_data['erv_out_map'], erv_total)


def compute_gatepass_in(raw_data, gatepass_total):
	return compute_erv(raw_data['gatepass_in_map'], gatepass_total)


def compute_erv(erv_map, erv_total, erv_mode=True):
	rows = []
	item_list = report_build_erv_item_map(erv_map)

	sr = 0
	for erv_no, erv_value in erv_map.items():
		sr += 1

		row = [sr, erv_no, erv_value.voucher.vehicle]
		if not erv_mode:
			row.extend([erv_value.voucher.driver])
		for item in item_list:
			if item in erv_value:
				row.append(erv_value[item])
				erv_total.setdefault(item, 0)
				erv_total[item] += erv_value[item]
			else:
				row.append("")

		rows.append(row)


	root.debug(erv_total)

	total_row = ['', '', 'Grand Total']
	for item in item_list:
		total_row.append(erv_total[item])

	rows.append(total_row)

	return rows


def compute_erv_totals(erv_map):
	aggr = {}
	for erv in erv_map.values():
		for item in items:
			if item in erv:
				aggr.setdefault(item, 0)
				aggr[item] += erv[item]

	return aggr


def compute_pr_totals(pr_map):
	return {}