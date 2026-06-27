document.addEventListener('DOMContentLoaded', () => {
  // Seleciona todos os elementos com a classe de animação
  const cards = document.querySelectorAll('.animate-card');

  // Adiciona a classe 'visible' em cascata
  cards.forEach((card, index) => {
    setTimeout(() => {
      card.classList.add('visible');
    }, index * 120);
  });
});
