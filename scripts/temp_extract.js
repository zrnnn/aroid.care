
    const fs = require('fs');
    const content = fs.readFileSync('../database.js', 'utf-8');
    // Mock missing DOM elements if necessary
    const document = {}; 
    const window = {};
    eval(content);
    console.log(JSON.stringify(plantsData));
    