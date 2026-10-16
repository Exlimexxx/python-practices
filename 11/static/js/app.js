// Клиентский скрипт афиши: подгружает рекомендации через API.
// Раздаётся CDN-сервером вместе с постерами и стилями.
(function () {
  "use strict";

  const RECOMMENDATIONS_TTL = 60; // секунд, совпадает с TTL кэша на сервере

  /**
   * Загружает рекомендации для фильма.
   * @param {number} movieId идентификатор фильма
   * @returns {Promise<Array>} список рекомендаций
   */
  async function loadRecommendations(movieId) {
    const response = await fetch("/api/recommendations?movie_id=" + movieId);
    if (!response.ok) {
      throw new Error("HTTP " + response.status);
    }
    return response.json();
  }

  /**
   * Рисует рекомендации в контейнере.
   */
  function render(container, items) {
    container.innerHTML = items
      .map((item) => '<a class="poster-card" href="/movie/' + item.id + '">' +
        '<img src="' + item.poster_path + '" alt="' + item.title + '" loading="lazy">' +
        "<span>" + item.title + "</span></a>")
      .join("");
  }

  document.addEventListener("DOMContentLoaded", function () {
    const container = document.getElementById("recommendations");
    if (!container) {
      return;
    }
    container.dataset.cacheTtl = String(RECOMMENDATIONS_TTL);
    loadRecommendations(1).then((items) => render(container, items)).catch(console.error);
  });
})();
