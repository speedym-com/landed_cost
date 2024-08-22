

frappe.ui.form.on("Stock Entry", {
    refresh: function (frm) {
        // erpnext.toggle_naming_series();

        // if (frm.doc.repost_required && frm.doc.docstatus === 1) {
        if (frm.doc.repost_required && frm.doc.docstatus === 1) {
            frm.set_intro(
                __(
                    "Stock and Accounting entries for this Stock Entry need to be reposted. Please click on 'Repost' button to update."
                )
            );
            frm.add_custom_button(__("Repost Stock and Accounting Entries"), () => {
                frm.call({
                    doc: frm.doc,
                    method: "repost_stock_entries",
                    freeze: true,
                    freeze_message: __("Reposting..."),
                    callback: (r) => {
                        if (!r.exc) {
                            frappe.msgprint(__("Stock and Accounting Entries are reposted."));
                            frm.refresh();
                        }
                    },
                });
            })
                .removeClass("btn-default")
                .addClass("btn-warning");
        }
    }
})