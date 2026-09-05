function toggleMenu() {
    document.getElementById('navLinks').classList.toggle('active');
}

function updateChips() {
    const checkboxes = document.querySelectorAll('input[name="ingredients"]:checked');
    const chipsContainer = document.getElementById('selectedChips');
    const emptyState = document.getElementById('emptyState');
    const countSpan = document.getElementById('ingCount');
    const findBtn = document.getElementById('findBtn');
    const aiBtn = document.getElementById('aiBtn');
    
    chipsContainer.innerHTML = '';
    
    if (checkboxes.length === 0) {
        chipsContainer.appendChild(emptyState);
        emptyState.style.display = 'block';
        countSpan.textContent = '(0 selected)';
        if(findBtn) findBtn.disabled = true;
        if(aiBtn) aiBtn.disabled = true;
        return;
    }
    
    if(findBtn) findBtn.disabled = false;
    if(aiBtn) aiBtn.disabled = false;
    countSpan.textContent = `(${checkboxes.length} selected)`;
    
    checkboxes.forEach(cb => {
        const chip = document.createElement('div');
        chip.className = 'chip';
        chip.innerHTML = `${cb.dataset.name} <span style="cursor:pointer; margin-left:5px;" onclick="removeIngredient('${cb.value}')">✖</span>`;
        chipsContainer.appendChild(chip);
    });
}

function removeIngredient(val) {
    const cb = document.querySelector(`input[name="ingredients"][value="${val}"]`);
    if(cb) {
        cb.checked = false;
        updateChips();
    }
}

function addIngredientRow() {
    const container = document.getElementById('ingredient-section');
    const template = document.getElementById('ing-template').innerHTML;
    container.insertAdjacentHTML('beforeend', template);
}

function addInstructionRow() {
    const container = document.getElementById('instruction-section');
    const template = document.getElementById('inst-template').innerHTML;
    container.insertAdjacentHTML('beforeend', template);
}

const foods = ['🍔', '🍕', '🌮', '🥕', '🧀', '🍅', '🍳', '🥑', '🍗', '🍩'];

function createFoodRain() {
    for (let i = 0; i < 30; i++) {
        setTimeout(() => {
            const food = document.createElement('div');
            food.classList.add('food-drop');
            food.innerText = foods[Math.floor(Math.random() * foods.length)];
            food.style.left = Math.random() * 100 + 'vw';
            food.style.animationDuration = (Math.random() * 2 + 1) + 's';
            document.body.appendChild(food);
            setTimeout(() => food.remove(), 3000);
        }, i * 100);
    }
}

function startAIChef() {
    const aiBtnText = document.getElementById('aiBtnText');
    aiBtnText.innerHTML = '<span class="cooking-text">👨‍🍳 AI is cooking...</span>';
    createFoodRain();
}
function addCustomIngredient() {
    const input = document.getElementById('customIngInput');
    const val = input.value.trim();
    if (!val) return; // Don't add empty text

    const chipsContainer = document.getElementById('selectedChips');
    const emptyState = document.getElementById('emptyState');
    const aiBtn = document.getElementById('aiBtn');
    
    // Hide the "No ingredients selected" text
    emptyState.style.display = 'none';

    // Create a unique ID for this custom item
    const uniqueId = 'custom_' + Date.now();

    // Create the visual chip
    const chip = document.createElement('div');
    chip.className = 'chip';
    chip.id = 'chip_' + uniqueId;
    chip.style.backgroundColor = 'var(--secondary)'; // Make custom chips green to stand out
    chip.innerHTML = `${val} <span style="cursor:pointer; margin-left:5px;" onclick="removeCustomIngredient('${uniqueId}')">✖</span>`;

    // Create a hidden input so Flask receives this data
    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = 'custom_ingredients'; // We will look for this name in Python
    hiddenInput.value = val;
    hiddenInput.id = 'input_' + uniqueId;

    // Add them to the screen and the form
    chipsContainer.appendChild(chip);
    document.getElementById('matchForm').appendChild(hiddenInput);

    // Clear the input box
    input.value = '';

    // Enable the AI button since we have ingredients!
    if(aiBtn) aiBtn.disabled = false;
}

function removeCustomIngredient(id) {
    // Remove the chip and the hidden input
    document.getElementById('chip_' + id).remove();
    document.getElementById('input_' + id).remove();

    // Check if we need to disable the buttons again
    const checkboxes = document.querySelectorAll('input[name="ingredients"]:checked');
    const customInputs = document.querySelectorAll('input[name="custom_ingredients"]');
    
    if (checkboxes.length === 0 && customInputs.length === 0) {
        document.getElementById('emptyState').style.display = 'block';
        document.getElementById('ingCount').textContent = '(0 selected)';
        if(document.getElementById('findBtn')) document.getElementById('findBtn').disabled = true;
        if(document.getElementById('aiBtn')) document.getElementById('aiBtn').disabled = true;
    }
}