document.addEventListener('DOMContentLoaded', () => {
    if (typeof Chart === 'undefined') return;

    const mesNode = document.getElementById('reservas-mes-data');
    const mesCanvas = document.getElementById('grafico-meses');
    if (mesNode && mesCanvas) {
        const dados = JSON.parse(mesNode.textContent);
        new Chart(mesCanvas, {
            type: 'line',
            data: {
                labels: dados.map((item) => item.mes),
                datasets: [{
                    label: 'Reservas',
                    data: dados.map((item) => item.total),
                    borderColor: '#5a1a1a',
                    backgroundColor: 'rgba(90, 26, 26, 0.15)',
                    fill: true,
                    tension: 0.25,
                }],
            },
            options: {responsive: true, maintainAspectRatio: false},
        });
    }

    const diaNode = document.getElementById('reservas-dia-data');
    const diaCanvas = document.getElementById('grafico-dias');
    if (diaNode && diaCanvas) {
        const dados = JSON.parse(diaNode.textContent);
        new Chart(diaCanvas, {
            type: 'bar',
            data: {
                labels: dados.map((item) => item.dia),
                datasets: [{
                    label: 'Reservas',
                    data: dados.map((item) => item.total),
                    backgroundColor: '#7a2a2a',
                }],
            },
            options: {responsive: true, maintainAspectRatio: false},
        });
    }
});
