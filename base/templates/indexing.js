var unaURL="{{ site_url }}/entry/new";

if (document.location.href.indexOf(unaURL) == -1) { 
    var title = document.title;
    var origPage = '';
    
    // FIXME: Does not work for framesets!
    var page = document.getElementsByTagName("html")[0];
    origPage = page.innerHTML;
    var doc = document;
    var body = doc.getElementsByTagName("body")[0];

    var unaDiv = doc.createElement("div");
    unaDiv.setAttribute("id", "unaBookmarklet");
    unaDiv.style.display = "none";

    var unaForm = doc.createElement("form");
    unaForm.setAttribute("action", unaURL);
    unaForm.setAttribute("method", "POST");
    unaForm.setAttribute("id", "unaForm");
    
    var unaDoIndex = doc.createElement("input");
    unaDoIndex.setAttribute("type", "checkbox");
    unaDoIndex.setAttribute("name", "do_index");
    unaDoIndex.setAttribute("value", "yes");
    unaDoIndex.setAttribute("checked", "checked");
    
    var unaContent = doc.createElement("textarea");
    unaContent.setAttribute("name", "content");
    unaContent.setAttribute("id", "id_content");
    unaContent.setAttribute("cols", 50);
    unaContent.setAttribute("rows", 4);
    
    var unaURL = doc.createElement("input");
    unaURL.setAttribute("type", "hidden");
    unaURL.setAttribute("name", "url");
    unaURL.setAttribute("id", "id_url");
    unaURL.setAttribute("value", doc.URL);
    
    var unaTitle = doc.createElement("input");
    unaTitle.setAttribute("type", "hidden");
    unaTitle.setAttribute("name", "title");
    unaTitle.setAttribute("id", "id_title");
    unaTitle.setAttribute("value", title);
    
    unaForm.appendChild(unaDoIndex);
    unaForm.appendChild(unaContent);
    unaForm.appendChild(unaURL);
    unaForm.appendChild(unaTitle);
    unaDiv.appendChild(unaForm);
    body.appendChild(unaDiv);
    
    doc.getElementById("id_content").value = origPage;
    doc.getElementById("unaForm").submit();
}
