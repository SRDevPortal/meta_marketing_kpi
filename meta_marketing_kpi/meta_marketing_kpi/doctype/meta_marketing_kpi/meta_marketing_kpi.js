frappe.ui.form.on("Meta Marketing KPI", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button("Ask AI Campaign Analyst", () => {
			openMetaAIChat({
				adName: frm.doc.ad_name,
				accountName: frm.doc.account_name,
				days: 60,
				initialQuestion: `Ad ${frm.doc.ad_name || frm.doc.ad_id} under account ${frm.doc.account_name || ""} is running good or not? What should I improve?`,
			});
		});
	},
});

function openMetaAIChat({ adName, accountName, days = 60, initialQuestion = "" }) {
	const messages = [];
	const dialog = new frappe.ui.Dialog({
		title: `AI Campaign Chat - ${adName || "Ad"}`,
		size: "large",
		fields: [
			{ fieldtype: "HTML", fieldname: "chat_html" },
			{
				fieldtype: "Small Text",
				fieldname: "question",
				label: "Ask a follow-up",
				reqd: 1,
				default: initialQuestion,
			},
		],
		primary_action_label: "Send",
		primary_action: () => sendQuestion(),
	});

	const chatField = dialog.get_field("chat_html");
	const chatHtml = chatField && chatField.$wrapper ? chatField.$wrapper : null;
	if (!chatHtml) {
		frappe.msgprint("Unable to open AI chat view. Please refresh and try again.");
		return;
	}

	chatHtml.css({
		maxHeight: "420px",
		overflowY: "auto",
		border: "1px solid #e5e7eb",
		borderRadius: "8px",
		padding: "12px",
		marginBottom: "8px",
		background: "#f8fafc",
	});

	const renderMessages = () => {
		const html = messages
			.map((item) => {
				if (item.role === "user") {
					return `<div style="text-align:right;margin:8px 0;"><div style="display:inline-block;background:#dbeafe;color:#1e3a8a;padding:8px 12px;border-radius:12px;max-width:85%;text-align:left;"><b>You:</b><br>${escapeHtml(item.text)}</div></div>`;
				}
				return `<div style="text-align:left;margin:8px 0;"><div style="display:inline-block;background:#ffffff;color:#111827;padding:10px 12px;border-radius:12px;max-width:90%;border:1px solid #e5e7eb;"><b>AI:</b><br>${formatAiAnswer(item.text)}<div style="margin-top:8px;color:#6b7280;font-size:12px;">Confidence: ${item.confidence || "N/A"}</div></div></div>`;
			})
			.join("");
		chatHtml.html(html || "<div style='color:#6b7280'>Start the conversation...</div>");
		chatHtml.scrollTop(chatHtml[0].scrollHeight);
	};

	const sendQuestion = () => {
		const question = (dialog.get_value("question") || "").trim();
		if (!question) return;

		messages.push({ role: "user", text: question });
		dialog.set_value("question", "");
		renderMessages();

		const composedQuestion = buildThreadQuestion(messages);
		frappe.call({
			method: "meta_marketing_kpi.meta_marketing_kpi.ai.api.ask_meta_campaign_ai",
			args: {
				account_name: accountName,
				ad_name: adName,
				question: composedQuestion,
				days,
			},
			freeze: true,
			freeze_message: "Analyzing campaign with KPI context...",
			callback: (r) => {
				const out = r.message || {};
				messages.push({ role: "assistant", text: out.answer || "No answer returned.", confidence: out.confidence });
				renderMessages();
			},
		});
	};

	dialog.show();
	renderMessages();
}

function buildThreadQuestion(messages) {
	const recent = messages.slice(-8);
	const lines = recent.map((item) => `${item.role === "user" ? "User" : "Assistant"}: ${item.text}`);
	lines.push("Answer the latest user question with campaign-specific KPI evidence from context.");
	return lines.join("\n");
}

function formatAiAnswer(text) {
	const safe = escapeHtml(text || "");
	const withHeadings = safe.replace(/^###\s*(.+)$/gm, "<h5 style='margin:8px 0 4px;'>$1</h5>");
	const withBold = withHeadings.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
	const lines = withBold.split("\n").map((line) => line.trim());
	let inList = false;
	let out = "";
	lines.forEach((line) => {
		if (!line) return;
		if (/^\d+\.\s+/.test(line) || /^-\s+/.test(line)) {
			if (!inList) {
				out += "<ul style='margin:6px 0 6px 18px;'>";
				inList = true;
			}
			out += `<li>${line.replace(/^\d+\.\s+/, "").replace(/^-\s+/, "")}</li>`;
		} else {
			if (inList) {
				out += "</ul>";
				inList = false;
			}
			out += `<p style='margin:4px 0;'>${line}</p>`;
		}
	});
	if (inList) out += "</ul>";
	return out;
}

function escapeHtml(value) {
	return (value || "")
		.replaceAll("&", "&amp;")
		.replaceAll("<", "&lt;")
		.replaceAll(">", "&gt;")
		.replaceAll('"', "&quot;")
		.replaceAll("'", "&#39;");
}
