# surveys/export_utils.py
"""
Export survey responses as CSV or PDF.

PDF colors roughly match the MNHP Survey frontend (green primary).
Keep this file plain — easier to tweak later.
"""

import csv
import io
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
	HRFlowable,
	KeepTogether,
	Paragraph,
	SimpleDocTemplate,
	Spacer,
	Table,
	TableStyle,
)

from .models import Answer, AnswerSelection, SurveyResponse

# --- brand / theme (close to frontend --primary lime/green) ---
PRIMARY = colors.HexColor("#65a30d")
PRIMARY_DARK = colors.HexColor("#4d7c0f")
PRIMARY_SOFT = colors.HexColor("#ecfccb")
HEADER_BG = colors.HexColor("#365314")
ROW_ALT = colors.HexColor("#f7fee7")
BORDER = colors.HexColor("#d9f99d")
MUTED = colors.HexColor("#64748b")
TEXT = colors.HexColor("#1a2e05")
WHITE = colors.white

SITE_NAME = "MNHP Survey"

# soft greens for pie slices
CHART_COLORS = [
	colors.HexColor("#65a30d"),
	colors.HexColor("#84cc16"),
	colors.HexColor("#4d7c0f"),
	colors.HexColor("#a3e635"),
	colors.HexColor("#3f6212"),
	colors.HexColor("#bef264"),
]


def _site_url():
	return getattr(settings, "FRONTEND_URL", "https://mnhp-survey.netlify.app").rstrip("/")


def _respondent_email(response):
	if response.respondent:
		return response.respondent.email
	return response.respondent_email or "Anonymous"


def _respondent_name(response):
	if not response.respondent:
		return ""
	name = f"{response.respondent.first_name} {response.respondent.last_name}".strip()
	return name


def _format_submitted_at(response):
	if not response.completed_at:
		return ""
	return response.completed_at.strftime("%Y-%m-%d %H:%M")


def _answer_text_for_question(response, question):
	answer = next(
		(a for a in response.answers.all() if a.question_id == question.id),
		None,
	)
	if not answer:
		return ""
	options = [
		sel.selected_option.option_text for sel in answer.selections.all()
	]
	return "; ".join(options)


def get_export_queryset(survey, row_limit=None):
	"""All complete responses, newest last. Optional row_limit caps how many we take."""
	qs = (
		SurveyResponse.objects.filter(survey=survey, is_complete=True)
		.select_related("respondent")
		.prefetch_related("answers__selections__selected_option")
		.order_by("completed_at")
	)
	if row_limit is not None and row_limit > 0:
		qs = qs[:row_limit]
	return qs


def _parse_export_options(options):
	"""
	Normalize options coming from the view.
	Expected keys:
	  - row_limit: int or None (None = all)
	  - include_summary: bool
	  - include_responses: bool
	  - chart_style: none | bar | pie | both
	"""
	options = options or {}
	row_limit = options.get("row_limit")
	if row_limit is not None:
		try:
			row_limit = int(row_limit)
			if row_limit <= 0:
				row_limit = None
		except (TypeError, ValueError):
			row_limit = None

	chart_style = (options.get("chart_style") or "bar").lower()
	if chart_style not in ("none", "bar", "pie", "both"):
		chart_style = "bar"

	return {
		"row_limit": row_limit,
		"include_summary": options.get("include_summary", True),
		"include_responses": options.get("include_responses", True),
		"chart_style": chart_style,
	}


# ============================================
# CSV
# ============================================
def build_csv_response(survey, options=None):
	opts = _parse_export_options(options)
	questions = list(survey.questions.all().order_by("order"))
	responses = list(get_export_queryset(survey, opts["row_limit"]))

	buffer = io.StringIO()
	writer = csv.writer(buffer)

	headers = ["SN", "Response ID", "Email", "Respondent Name", "Submitted At"]
	headers.extend([q.question_text for q in questions])
	writer.writerow(headers)

	for index, response in enumerate(responses, start=1):
		row = [
			index,
			str(response.id),
			_respondent_email(response),
			_respondent_name(response),
			_format_submitted_at(response),
		]
		for question in questions:
			row.append(_answer_text_for_question(response, question))
		writer.writerow(row)

	filename = f"{_safe_filename(survey.title)}_responses.csv"
	http_response = HttpResponse(
		buffer.getvalue(),
		content_type="text/csv; charset=utf-8",
	)
	http_response["Content-Disposition"] = f'attachment; filename="{filename}"'
	return http_response


# ============================================
# PDF
# ============================================
def build_pdf_response(survey, options=None):
	opts = _parse_export_options(options)
	questions = list(survey.questions.all().order_by("order"))
	# full count for the header (before applying row limit)
	total_all = SurveyResponse.objects.filter(
		survey=survey, is_complete=True
	).count()
	responses = list(get_export_queryset(survey, opts["row_limit"]))

	buffer = io.BytesIO()
	doc = SimpleDocTemplate(
		buffer,
		pagesize=landscape(A4),
		leftMargin=0.55 * inch,
		rightMargin=0.55 * inch,
		topMargin=0.5 * inch,
		bottomMargin=0.55 * inch,
		title=f"{survey.title} — Responses",
		author=SITE_NAME,
	)

	styles = _pdf_styles()
	story = []

	# brand header
	story.extend(_build_pdf_header(survey, total_all, len(responses), styles))

	# summary + optional charts
	if opts["include_summary"]:
		story.append(Paragraph("Summary by Question", styles["section"]))
		story.append(Spacer(1, 6))

		for question in questions:
			block = _build_question_summary_block(
				survey, question, styles, opts["chart_style"]
			)
			story.append(KeepTogether(block))
			story.append(Spacer(1, 12))

	# individual rows
	if opts["include_responses"]:
		story.append(Paragraph("Individual Responses", styles["section"]))
		story.append(Spacer(1, 4))

		if opts["row_limit"] and total_all > len(responses):
			story.append(
				Paragraph(
					f"Showing {len(responses)} of {total_all} responses "
					f"(row limit applied).",
					styles["muted"],
				)
			)
			story.append(Spacer(1, 6))

		story.extend(_build_responses_table(questions, responses, styles))

	# footer note
	story.append(Spacer(1, 16))
	story.append(
		HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=6)
	)
	story.append(
		Paragraph(
			f'Exported from <link href="{_site_url()}">'
			f'<font color="#65a30d"><u>{SITE_NAME}</u></font></link>',
			styles["footer"],
		)
	)

	doc.build(story)
	buffer.seek(0)

	filename = f"{_safe_filename(survey.title)}_responses.pdf"
	http_response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
	http_response["Content-Disposition"] = f'attachment; filename="{filename}"'
	return http_response


def _pdf_styles():
	base = getSampleStyleSheet()

	return {
		"brand": ParagraphStyle(
			"Brand",
			parent=base["Normal"],
			fontSize=11,
			textColor=PRIMARY_DARK,
			alignment=TA_LEFT,
			spaceAfter=2,
			fontName="Helvetica-Bold",
		),
		"title": ParagraphStyle(
			"ExportTitle",
			parent=base["Heading1"],
			fontSize=18,
			textColor=TEXT,
			alignment=TA_LEFT,
			spaceAfter=4,
			spaceBefore=2,
			leading=22,
		),
		"meta": ParagraphStyle(
			"ExportMeta",
			parent=base["Normal"],
			fontSize=9,
			textColor=MUTED,
			alignment=TA_LEFT,
			spaceAfter=10,
		),
		"section": ParagraphStyle(
			"SectionHeading",
			parent=base["Heading2"],
			fontSize=13,
			textColor=PRIMARY_DARK,
			spaceBefore=4,
			spaceAfter=4,
			fontName="Helvetica-Bold",
		),
		"question": ParagraphStyle(
			"QuestionTitle",
			parent=base["Normal"],
			fontSize=9,
			textColor=TEXT,
			leading=12,
			spaceAfter=4,
			fontName="Helvetica-Bold",
		),
		"body": ParagraphStyle(
			"BodySmall",
			parent=base["Normal"],
			fontSize=8,
			leading=10,
			textColor=TEXT,
			alignment=TA_LEFT,
		),
		"muted": ParagraphStyle(
			"Muted",
			parent=base["Normal"],
			fontSize=8,
			textColor=MUTED,
			spaceAfter=4,
		),
		"footer": ParagraphStyle(
			"Footer",
			parent=base["Normal"],
			fontSize=8,
			textColor=MUTED,
			alignment=TA_CENTER,
		),
		"th": ParagraphStyle(
			"TableHeader",
			parent=base["Normal"],
			fontSize=8,
			textColor=WHITE,
			fontName="Helvetica-Bold",
			leading=10,
		),
	}


def _build_pdf_header(survey, total_all, exported_count, styles):
	"""Top of the PDF: clickable site name + survey title + meta."""
	site = _site_url()
	brand = Paragraph(
		f'<link href="{site}"><font color="#65a30d"><u>{SITE_NAME}</u></font></link>',
		styles["brand"],
	)
	title = Paragraph(_escape(survey.title), styles["title"])

	meta_bits = [
		f"Total responses: {total_all}",
		f"Included in this file: {exported_count}",
		f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
	]
	meta = Paragraph("  ·  ".join(meta_bits), styles["meta"])

	# little green accent bar on the left via a 2-col table
	accent = Table(
		[["", [brand, title, meta]]],
		colWidths=[0.12 * inch, 10.2 * inch],
	)
	accent.setStyle(
		TableStyle(
			[
				("BACKGROUND", (0, 0), (0, 0), PRIMARY),
				("VALIGN", (0, 0), (-1, -1), "TOP"),
				("LEFTPADDING", (1, 0), (1, 0), 10),
				("RIGHTPADDING", (0, 0), (-1, -1), 0),
				("TOPPADDING", (0, 0), (-1, -1), 4),
				("BOTTOMPADDING", (0, 0), (-1, -1), 4),
				("BACKGROUND", (1, 0), (1, 0), PRIMARY_SOFT),
			]
		)
	)

	return [
		accent,
		Spacer(1, 14),
		HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=12),
	]


def _question_option_stats(survey, question):
	"""Return (total_answers, [{label, count, percentage}, ...])."""
	total_answers = Answer.objects.filter(
		response__survey=survey,
		response__is_complete=True,
		question=question,
	).count()

	rows = []
	for option in question.options.all().order_by("order"):
		count = AnswerSelection.objects.filter(
			answer__response__survey=survey,
			answer__response__is_complete=True,
			answer__question=question,
			selected_option=option,
		).count()
		pct = round(count / total_answers * 100, 1) if total_answers else 0
		rows.append(
			{
				"label": option.option_text,
				"count": count,
				"percentage": pct,
			}
		)
	return total_answers, rows


def _build_question_summary_block(survey, question, styles, chart_style):
	"""One question: title, stats table, optional bar/pie chart."""
	total_answers, option_rows = _question_option_stats(survey, question)
	parts = []

	q_type = question.question_type.replace("_", " ")
	parts.append(
		Paragraph(
			f"{_escape(question.question_text)} "
			f'<font color="#64748b" size="8">({q_type} · {total_answers} answers)</font>',
			styles["question"],
		)
	)

	# stats table
	table_data = [
		[
			Paragraph("Option", styles["th"]),
			Paragraph("Count", styles["th"]),
			Paragraph("%", styles["th"]),
		]
	]
	for row in option_rows:
		table_data.append(
			[
				Paragraph(_escape(row["label"]), styles["body"]),
				Paragraph(str(row["count"]), styles["body"]),
				Paragraph(f"{row['percentage']}%", styles["body"]),
			]
		)

	stats_table = Table(
		table_data, colWidths=[4.2 * inch, 0.7 * inch, 0.7 * inch]
	)
	stats_table.setStyle(_brand_table_style())
	parts.append(stats_table)

	# charts (skip if no answers or chart_style is none)
	if chart_style != "none" and option_rows and total_answers > 0:
		parts.append(Spacer(1, 6))
		chart_row = []
		if chart_style in ("bar", "both"):
			chart_row.append(_make_bar_chart(option_rows))
		if chart_style in ("pie", "both"):
			chart_row.append(_make_pie_chart(option_rows))

		if len(chart_row) == 1:
			parts.append(chart_row[0])
		elif len(chart_row) == 2:
			charts = Table([chart_row], colWidths=[5.2 * inch, 4.8 * inch])
			charts.setStyle(
				TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")])
			)
			parts.append(charts)

	return parts


def _make_bar_chart(option_rows):
	"""Simple horizontal bar chart using reportlab."""
	drawing = Drawing(360, 120)
	chart = HorizontalBarChart()
	chart.x = 90
	chart.y = 10
	chart.height = 95
	chart.width = 250

	data = [[row["count"] for row in option_rows]]
	chart.data = data
	chart.categoryAxis.categoryNames = [
		_short_label(row["label"], 18) for row in option_rows
	]
	chart.bars[0].fillColor = PRIMARY
	chart.bars[0].strokeColor = PRIMARY_DARK
	chart.valueAxis.valueMin = 0
	max_count = max((row["count"] for row in option_rows), default=1)
	chart.valueAxis.valueMax = max(max_count, 1) * 1.15
	chart.categoryAxis.labels.fontSize = 7
	chart.valueAxis.labels.fontSize = 7

	drawing.add(chart)
	drawing.add(
		String(90, 110, "Bar chart", fontSize=8, fillColor=PRIMARY_DARK)
	)
	return drawing


def _make_pie_chart(option_rows):
	"""Simple pie chart using reportlab."""
	drawing = Drawing(280, 130)
	pie = Pie()
	pie.x = 35
	pie.y = 15
	pie.width = 100
	pie.height = 100
	pie.data = [row["count"] for row in option_rows]
	pie.labels = [
		_short_label(row["label"], 14) for row in option_rows
	]
	pie.sideLabels = True
	pie.simpleLabels = False
	pie.slices.strokeWidth = 0.5
	pie.slices.strokeColor = WHITE

	for i in range(len(option_rows)):
		pie.slices[i].fillColor = CHART_COLORS[i % len(CHART_COLORS)]

	drawing.add(pie)
	drawing.add(
		String(35, 118, "Pie chart", fontSize=8, fillColor=PRIMARY_DARK)
	)
	return drawing


def _build_responses_table(questions, responses, styles):
	if not responses:
		return [Paragraph("No completed responses yet.", styles["muted"])]

	# too many question columns get unreadable — show Q1, Q2… with a key
	use_short_headers = len(questions) > 4

	header = [
		Paragraph("SN", styles["th"]),
		Paragraph("Email", styles["th"]),
		Paragraph("Submitted", styles["th"]),
	]
	for i, question in enumerate(questions, start=1):
		if use_short_headers:
			label = f"Q{i}"
		else:
			label = _short_label(question.question_text, 28)
		header.append(Paragraph(_escape(label), styles["th"]))

	table_data = [header]

	available = 10.3 * inch
	meta = 2.5 * inch
	q_width = (
		(available - meta) / len(questions) if questions else available - meta
	)
	col_widths = [0.35 * inch, 1.45 * inch, 0.7 * inch] + [
		q_width for _ in questions
	]

	for index, response in enumerate(responses, start=1):
		row = [
			Paragraph(str(index), styles["body"]),
			Paragraph(_escape(_respondent_email(response)), styles["body"]),
			Paragraph(_escape(_format_submitted_at(response)), styles["body"]),
		]
		for question in questions:
			row.append(
				Paragraph(
					_escape(_answer_text_for_question(response, question)),
					styles["body"],
				)
			)
		table_data.append(row)

	table = Table(table_data, colWidths=col_widths, repeatRows=1)
	table.setStyle(_brand_table_style(font_size=7))

	parts = [table]

	# legend when we shortened headers
	if use_short_headers:
		parts.append(Spacer(1, 8))
		parts.append(Paragraph("Question key", styles["muted"]))
		for i, question in enumerate(questions, start=1):
			parts.append(
				Paragraph(
					f"<b>Q{i}</b> — {_escape(question.question_text)}",
					styles["body"],
				)
			)

	return parts


def _brand_table_style(font_size=8):
	return TableStyle(
		[
			("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
			("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
			("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
			("FONTSIZE", (0, 0), (-1, -1), font_size),
			("GRID", (0, 0), (-1, -1), 0.4, BORDER),
			("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ROW_ALT]),
			("VALIGN", (0, 0), (-1, -1), "TOP"),
			("LEFTPADDING", (0, 0), (-1, -1), 4),
			("RIGHTPADDING", (0, 0), (-1, -1), 4),
			("TOPPADDING", (0, 0), (-1, -1), 3),
			("BOTTOMPADDING", (0, 0), (-1, -1), 3),
		]
	)


def _short_label(text, max_len):
	text = str(text or "")
	if len(text) <= max_len:
		return text
	return text[: max_len - 1] + "…"


def _safe_filename(title):
	cleaned = "".join(
		c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title
	)
	cleaned = "_".join(cleaned.split())[:60] or "survey"
	return cleaned


def _escape(text):
	if text is None:
		return ""
	return (
		str(text)
		.replace("&", "&amp;")
		.replace("<", "&lt;")
		.replace(">", "&gt;")
	)
