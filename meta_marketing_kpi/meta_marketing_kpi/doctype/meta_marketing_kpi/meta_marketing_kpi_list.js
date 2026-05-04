frappe.listview_settings["Meta Marketing KPI"] = {
	onload(listview) {
		listview.page.add_inner_button("Ask AI Campaign Analyst", () => {
			frappe.call({
				method: "meta_marketing_kpi.meta_marketing_kpi.ai.api.get_meta_filter_options",
				callback: (r) => {
					const data = r.message || {};
					const adOptions = (data.ad_names || []).filter(Boolean);
					const accountOptions = (data.account_names || []).filter(Boolean);

					if (!adOptions.length) {
						frappe.msgprint("No ad names found in Meta Marketing KPI data.");
						return;
					}
					if (!accountOptions.length) {
						frappe.msgprint("No account names found in Meta Marketing KPI data.");
						return;
					}

					frappe.prompt(
						[
							{
								fieldname: "account_name",
								label: "Account Name",
								fieldtype: "Select",
								reqd: 1,
								options: accountOptions.join("\n"),
								default: accountOptions[0],
							},
							{
								fieldname: "ad_name",
								label: "Ad Name",
								fieldtype: "Select",
								reqd: 1,
								options: adOptions.join("\n"),
								default: adOptions[0],
							},
							{
								fieldname: "question",
								label: "Question",
								fieldtype: "Small Text",
								reqd: 1,
								default: "Is this campaign running good or not? What should I improve?",
							},
						],
						(values) => {
							openMetaAIChat({
								adName: values.ad_name,
								accountName: values.account_name,
								initialQuestion: values.question,
								days: 60,
							});
						},
						"Ask AI Campaign Analyst",
						"Open Chat"
					);
				},
			});
		});
	},
};

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
