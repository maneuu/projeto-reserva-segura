document.addEventListener('DOMContentLoaded', () => {
  // Seleciona todos os cards que possuem a classe de animação
  const cards = document.querySelectorAll('.animate-card');

  // Aplica a classe 'visible' com um pequeno atraso progressivo para criar um efeito de cascata
  cards.forEach((card, index) => {
    setTimeout(() => {
      card.classList.add('visible');
    }, index * 150); // 150ms de diferença entre a entrada de cada card
  });
});
