const fs = require('fs');

let content = fs.readFileSync('/mnt/Data/The Lab/Coding/PlantCare/database.js', 'utf8');

// Replacements for the boilerplate in feat:
const monsterPattern = /The majestic Monstera.*?the lower leaves\.\s*/g;
const philoPattern = /Hailing from the misty.*?creeping jungle aesthetic\.\s*/g;
const anthuriumPattern = /The exquisite Anthurium.*?living art\.\s*/g;
const alocasiaPattern = /Known for its striking.*?prevent tuber rot\.\s*/g;
const syngoniumPattern = /Originating from the vibrant.*?vibrant foliage\.\s*/g;
const hoyaPattern = /The delicate and beautiful Hoya.*?succulent-like leaves\.\s*/g;
const genericPattern = /The fascinating.*?stunning visual appeal\.\s*/g;

content = content.replace(monsterPattern, '');
content = content.replace(philoPattern, '');
content = content.replace(anthuriumPattern, '');
content = content.replace(alocasiaPattern, '');
content = content.replace(syngoniumPattern, '');
content = content.replace(hoyaPattern, '');
content = content.replace(genericPattern, '');

// Philodendron verrucosum origin
content = content.replace(/n: 'Philodendron verrucosum'(.*?)origin: 'Central America'/g, "n: 'Philodendron verrucosum'$1origin: 'Ecuador, Colombia, Peru'");
// Philodendron spiritus sancti
content = content.replace(/aerodynamic leaves are perfectly evolved to withstand high canopy winds/, 'narrow leaves are perfectly evolved to withstand high canopy winds and shade competition');
// Hoya callistophylla
content = content.replace(/n: 'Hoya callistophylla'(.*?)lvl: 'Expert'/g, "n: 'Hoya callistophylla'$1lvl: 'Advanced'");
// Hoya polyneura
content = content.replace(/n: 'Hoya polyneura \\'Albomarginata\\''(.*?)origin: 'Himalayas'/g, "n: 'Hoya polyneura \\'Albomarginata\\''$1origin: 'Himalayas / SW China'");
// Anthurium veitchii habitat
content = content.replace(/n: 'Anthurium veitchii'(.*?)habitat: 'Canopy Epiphyte'/g, "n: 'Anthurium veitchii'$1habitat: 'Canopy Epiphyte, Colombia'");

// Non-Aroid labels
const nonAroids = [
    'Hoya carnosa \\'Compacta Regalis\\'',
    'Hoya australis \\'Lisa\\'',
    'Hoya callistophylla',
    'Hoya kerrii \\'Variegata\\'',
    'Hoya polyneura \\'Albomarginata\\'',
    'Hoya wayetii \\'Variegata\\'',
    'Strelitzia nicolai',
    'Strelitzia reginae',
    'Stromanthe thalia \\'Triostar\\'',
    'Begonia chlorosticta'
];

nonAroids.forEach(name => {
    const regex = new RegExp(`n: '${name}'`, 'g');
    content = content.replace(regex, `n: '${name} (Non-Aroid)'`);
});

fs.writeFileSync('/mnt/Data/The Lab/Coding/PlantCare/database.js', content);
console.log("Database updated.");
