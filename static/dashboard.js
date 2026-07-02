
document.addEventListener("DOMContentLoaded", () => {

  if (typeof Chart === "undefined") return;

  const lucro = document.getElementById("lucroChart");
  if (lucro) {
    new Chart(lucro, {
      type: "line",
      data: {
        labels: ["Jan","Fev","Mar","Abr","Mai","Jun"],
        datasets: [{
          label: "Lucro",
          data: [0,0,0,0,0,0],
          borderColor: "#4d8cff",
          tension: 0.3
        }]
      },
      options: {responsive:true, plugins:{legend:{display:false}}}
    });
  }

  const premios = document.getElementById("premiosChart");
  if (premios) {
    new Chart(premios, {
      type: "bar",
      data: {
        labels: ["Jan","Fev","Mar","Abr","Mai","Jun"],
        datasets: [{
          data: [0,0,0,0,0,0],
          backgroundColor: "#46e85b"
        }]
      },
      options: {responsive:true, plugins:{legend:{display:false}}}
    });
  }

  const pizza = document.getElementById("pizzaChart");
  if (pizza) {
    new Chart(pizza, {
      type: "doughnut",
      data: {
        labels: ["Sem dados"],
        datasets: [{
          data: [100]
        }]
      },
      options: {responsive:true}
    });
  }

});
