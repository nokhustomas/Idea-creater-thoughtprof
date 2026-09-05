// JavaScript snippet: Event handler
function handleClick(event) {
    console.log('Button clicked:', event.target.id);
    return { status: 'success' };
}

// JavaScript snippet: Array processing
function filterItems(items, criteria) {
    return items.filter(item => item.type === criteria);
}
