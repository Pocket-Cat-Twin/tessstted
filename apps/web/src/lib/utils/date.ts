// Date utility functions

export function formatDate(dateString: string | Date): string {
  if (!dateString) return "";

  const date =
    typeof dateString === "string" ? new Date(dateString) : dateString;

  if (isNaN(date.getTime())) {
    return "";
  }

  // Russian date format
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "Europe/Moscow",
  };

  return date.toLocaleDateString("ru-RU", options);
}

export function formatDateTime(dateString: string | Date): string {
  if (!dateString) return "";

  const date =
    typeof dateString === "string" ? new Date(dateString) : dateString;

  if (isNaN(date.getTime())) {
    return "";
  }

  // Russian date and time format
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Moscow",
  };

  return date.toLocaleDateString("ru-RU", options);
}

export function formatShortDate(dateString: string | Date): string {
  if (!dateString) return "";

  const date =
    typeof dateString === "string" ? new Date(dateString) : dateString;

  if (isNaN(date.getTime())) {
    return "";
  }

  // Short date format
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "Europe/Moscow",
  };

  return date.toLocaleDateString("ru-RU", options);
}

export function formatRelativeTime(dateString: string | Date): string {
  if (!dateString) return "";

  const date =
    typeof dateString === "string" ? new Date(dateString) : dateString;

  if (isNaN(date.getTime())) {
    return "";
  }

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return "сегодня";
  } else if (diffDays === 1) {
    return "вчера";
  } else if (diffDays < 7) {
    return `${diffDays} дня назад`;
  } else if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks} недели назад`;
  } else {
    return formatShortDate(date);
  }
}

export function isToday(dateString: string | Date): boolean {
  if (!dateString) return false;

  const date =
    typeof dateString === "string" ? new Date(dateString) : dateString;

  if (isNaN(date.getTime())) {
    return false;
  }

  const today = new Date();
  return date.toDateString() === today.toDateString();
}

export function isValidDate(dateString: string | Date): boolean {
  if (!dateString) return false;

  const date =
    typeof dateString === "string" ? new Date(dateString) : dateString;

  return !isNaN(date.getTime());
}
