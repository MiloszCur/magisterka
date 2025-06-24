let currentKeywordIndex = -1;
let keywordMatches = [];
let currentKeyword = '';
let currentActTitle = '';

function toggleTree(event) {
    const children = event.target.nextElementSibling;
    if (children.style.display === 'none') {
        children.style.display = 'block';
    } else {
        children.style.display = 'none';
    }
}

function fetchActs() {
    const publisher = document.getElementById("publisher").value;
    const year = document.getElementById("year").value;
    const count = document.getElementById("count").value;

    document.getElementById("acts-tree").innerHTML = "";
    $(".loader-spinner").show();

    fetch(`/fetch_acts?publisher=${publisher}&year=${year}&count=${count}`)
        .then((response) => response.json())
        .then((data) => {
            renderTree(data);
            $(".loader-spinner").hide();
        })
        .catch((error) => {
            console.error("Error fetching acts:", error);
            $(".loader-spinner").hide();
        });
}

function renderTree(data) {
    const treeContainer = document.getElementById("acts-tree");

    const ul = document.createElement("ul");
    data.forEach((act) => {
        const li = document.createElement("li");
        li.textContent = act.title;
        li.onclick = function () {
            fetchActText(act.title, act.pdf_url);
        };
        ul.appendChild(li);
    });
    treeContainer.appendChild(ul);
}

function fetchActText(title, pdfUrl) {
    currentActTitle = title;
    currentKeywordIndex = -1;
    keywordMatches = [];

    fetch(`/extract_text?pdf_url=${encodeURIComponent(pdfUrl)}`)
        .then((response) => response.text())
        .then((text) => {
            renderPDFText(text, pdfUrl);
        })
        .catch((error) => {
            console.error("Error extracting text:", error);
        });
}

function renderPDFText(text, pdfUrl) {
    const keywords = ["art.", "ust.", "pkt"];
    const modal = document.getElementById("pdf-modal");
    const modalContent = document.getElementById("modal-content");
    const iframe = document.createElement("iframe");

    iframe.src = pdfUrl;
    modalContent.innerHTML = "";
    modalContent.appendChild(iframe);
    modal.style.display = "block";

    currentKeyword = prompt("Enter keyword to search (e.g., 'art.'):", "art.");
    if (!currentKeyword) return;

    keywordMatches = getKeywordMatches(text, currentKeyword);

    if (keywordMatches.length > 0) {
        currentKeywordIndex = 0;
        alert("Found " + keywordMatches.length + " matches.");
        scrollToKeyword(keywordMatches[currentKeywordIndex]);
    } else {
        alert("No matches found.");
    }
}

function getKeywordMatches(text, keyword) {
    const regex = new RegExp(keyword, "gi");
    let matches = [];
    let match;
    while ((match = regex.exec(text)) !== null) {
        matches.push({ index: match.index, match: match[0] });
    }
    return matches;
}

function scrollToKeyword(match) {
    console.log("Scroll to index:", match.index);
    // Można tu dodać bardziej zaawansowaną nawigację w dokumencie PDF
}

document.getElementById("close-modal").onclick = function () {
    document.getElementById("pdf-modal").style.display = "none";
};

document.getElementById("prev-keyword").onclick = function () {
    if (keywordMatches.length === 0) return;
    currentKeywordIndex =
        (currentKeywordIndex - 1 + keywordMatches.length) % keywordMatches.length;
    scrollToKeyword(keywordMatches[currentKeywordIndex]);
};

document.getElementById("next-keyword").onclick = function () {
    if (keywordMatches.length === 0) return;
    currentKeywordIndex = (currentKeywordIndex + 1) % keywordMatches.length;
    scrollToKeyword(keywordMatches[currentKeywordIndex]);
};
