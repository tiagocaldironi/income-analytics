export function setTodayAsDefault() {
  const today = new Date().toLocaleDateString("en-CA");
  ["#effective-date", "#quote-date", "#cdi-date"].forEach(selector => {
    const input = document.querySelector(selector);
    if (input) input.value = today;
  });

  setUnderstandDefaultPeriod();
}

function toLocalIsoDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function previousCalendarMonth(today = new Date()) {
  return {
    start: toLocalIsoDate(new Date(today.getFullYear(), today.getMonth() - 1, 1)),
    end: toLocalIsoDate(new Date(today.getFullYear(), today.getMonth(), 0)),
  };
}

export function setUnderstandDefaultPeriod(
  today = new Date(),
  search = window.location.search,
) {
  const startInput = document.querySelector("#wealth-start-date");
  const endInput = document.querySelector("#wealth-end-date");
  if (!startInput || !endInput || startInput.value || endInput.value) return;

  const params = new URLSearchParams(search);
  const explicitStart = params.get("start_date");
  const explicitEnd = params.get("end_date");
  const fallback = previousCalendarMonth(today);

  startInput.value = explicitStart && explicitEnd ? explicitStart : fallback.start;
  endInput.value = explicitStart && explicitEnd ? explicitEnd : fallback.end;
}
