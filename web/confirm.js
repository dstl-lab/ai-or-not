/** In-page confirmation with modal keyboard behavior and an explicit safe default. */
export function confirmAction({title, message, confirmLabel}) {
  return new Promise(resolve => {
    const dialog = document.createElement("dialog");
    dialog.className = "confirmation-dialog";
    const heading = document.createElement("h2");
    heading.id = "confirmation-title";
    heading.textContent = title;
    const description = document.createElement("p");
    description.id = "confirmation-message";
    description.textContent = message;
    dialog.setAttribute("aria-labelledby", heading.id);
    dialog.setAttribute("aria-describedby", description.id);

    const actions = document.createElement("div");
    actions.className = "confirmation-actions";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = "Cancel";
    cancel.autofocus = true;
    cancel.addEventListener("click", () => dialog.close("cancel"));
    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "primary";
    accept.textContent = confirmLabel;
    accept.addEventListener("click", () => dialog.close("confirm"));
    actions.append(cancel, accept);
    dialog.append(heading, description, actions);
    dialog.addEventListener("cancel", event => {
      event.preventDefault();
      dialog.close("cancel");
    });
    dialog.addEventListener("close", () => {
      const accepted = dialog.returnValue === "confirm";
      dialog.remove();
      resolve(accepted);
    }, {once:true});
    document.body.append(dialog);
    dialog.showModal();
    cancel.focus();
  });
}
