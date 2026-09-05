// Gestion des notifications push pour Realm

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

async function activerNotifications() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    alert("Les notifications ne sont pas supportées sur ce navigateur.");
    return;
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    alert("Tu as refusé les notifications. Tu peux les réactiver plus tard dans les réglages du navigateur.");
    return;
  }

  const registration = await navigator.serviceWorker.ready;

  const reponse = await fetch("/notifications/cle_publique");
  const { cle_publique } = await reponse.json();

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(cle_publique),
  });

  await fetch("/notifications/abonner", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(subscription),
  });

  const bouton = document.getElementById("bouton-notifications");
  if (bouton) {
    bouton.textContent = "🔔 Notifications activées";
    bouton.disabled = true;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const bouton = document.getElementById("bouton-notifications");
  if (bouton) {
    bouton.addEventListener("click", activerNotifications);
  }

  // Si déjà autorisé précédemment, on met à jour le libellé du bouton
  if ("Notification" in window && Notification.permission === "granted" && bouton) {
    bouton.textContent = "🔔 Notifications activées";
  }
});
