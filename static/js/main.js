document.addEventListener("DOMContentLoaded", () => {
  const buttons = document.querySelectorAll(".tab-button");
  const panels = document.querySelectorAll(".snapshot-panel");

  if (!buttons.length) {
    return;
  }

  function activateTab(index) {
    buttons.forEach((button, i) => {
      button.setAttribute("aria-selected", i === index);
    });

    panels.forEach((panel) => {
      const panelIndex = parseInt(panel.dataset.index, 10);
      panel.hidden = panelIndex !== index;
    });
  }

  buttons.forEach((button, index) => {
    button.addEventListener("click", () => activateTab(index));
  });

  activateTab(0);
});
