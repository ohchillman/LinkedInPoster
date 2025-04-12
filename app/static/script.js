document.addEventListener('DOMContentLoaded', function() {
    // Toggle proxy fields visibility
    document.getElementById('useProxy').addEventListener('change', function() {
        document.getElementById('proxyFields').style.display = this.checked ? 'block' : 'none';
    });
    
    // Toggle proxy type fields
    document.getElementById('httpProxyType').addEventListener('change', function() {
        if (this.checked) {
            document.getElementById('httpProxyFields').style.display = 'block';
            document.getElementById('socks5ProxyFields').style.display = 'none';
        }
    });
    
    document.getElementById('socks5ProxyType').addEventListener('change', function() {
        if (this.checked) {
            document.getElementById('httpProxyFields').style.display = 'none';
            document.getElementById('socks5ProxyFields').style.display = 'block';
        }
    });
    
    // Handle form submission
    document.getElementById('linkedinForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Show loading spinner
        document.getElementById('loading').style.display = 'block';
        document.getElementById('response').style.display = 'none';
        document.getElementById('submitBtn').disabled = true;
        
        // Get form data
        const clientId = document.getElementById('client_id').value;
        const clientSecret = document.getElementById('client_secret').value;
        const accessToken = document.getElementById('access_token').value;
        const postText = document.getElementById('postText').value;
        const useProxy = document.getElementById('useProxy').checked;
        
        // Prepare request data
        let requestData = {
            client_id: clientId,
            client_secret: clientSecret,
            access_token: accessToken,
            text: postText
        };
        
        // Add proxy if enabled
        if (useProxy) {
            const proxyType = document.querySelector('input[name="proxyType"]:checked').value;
            
            if (proxyType === 'http') {
                const httpProxy = document.getElementById('httpProxy').value;
                const httpsProxy = document.getElementById('httpsProxy').value;
                
                if (httpProxy || httpsProxy) {
                    requestData.proxy = {};
                    if (httpProxy) requestData.proxy.http = httpProxy;
                    if (httpsProxy) requestData.proxy.https = httpsProxy;
                }
            } else if (proxyType === 'socks5') {
                const socks5Proxy = document.getElementById('socks5Proxy').value;
                
                if (socks5Proxy) {
                    requestData.proxy = {
                        socks5: socks5Proxy
                    };
                }
            }
        }
        
        // Handle image if selected
        const imageFile = document.getElementById('imageFile').files[0];
        if (imageFile) {
            const reader = new FileReader();
            reader.onload = function(event) {
                // Get base64 data without the prefix
                const base64Image = event.target.result.split(',')[1];
                requestData.image = base64Image;
                sendPostRequest(requestData);
            };
            reader.readAsDataURL(imageFile);
        } else {
            sendPostRequest(requestData);
        }
    });
    
    function sendPostRequest(requestData) {
        fetch('/api/post', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading spinner
            document.getElementById('loading').style.display = 'none';
            document.getElementById('submitBtn').disabled = false;
            
            // Show response
            const responseElement = document.getElementById('response');
            responseElement.style.display = 'block';
            
            if (data.status === 'success') {
                responseElement.className = 'response success';
                document.getElementById('responseTitle').textContent = 'Post Published Successfully!';
                document.getElementById('responseMessage').textContent = 'Post ID: ' + data.post_id;
                
                // Show post link
                const postLink = document.getElementById('postLink');
                postLink.href = data.post_url;
                postLink.textContent = 'View Post';
                postLink.style.display = 'block';
            } else {
                responseElement.className = 'response error';
                document.getElementById('responseTitle').textContent = 'Error';
                document.getElementById('responseMessage').textContent = data.message;
                document.getElementById('postLink').style.display = 'none';
            }
            
            // Display request and response details
            if (data.request) {
                document.getElementById('requestDetails').textContent = JSON.stringify(data.request, null, 2);
            }
            
            if (data.response) {
                document.getElementById('responseDetails').textContent = JSON.stringify(data.response, null, 2);
            }
        })
        .catch(error => {
            // Hide loading spinner
            document.getElementById('loading').style.display = 'none';
            document.getElementById('submitBtn').disabled = false;
            
            // Show error
            const responseElement = document.getElementById('response');
            responseElement.style.display = 'block';
            responseElement.className = 'response error';
            document.getElementById('responseTitle').textContent = 'Error';
            document.getElementById('responseMessage').textContent = 'Failed to connect to the server: ' + error.message;
            document.getElementById('postLink').style.display = 'none';
            
            // Clear request and response details
            document.getElementById('requestDetails').textContent = '';
            document.getElementById('responseDetails').textContent = '';
        });
    }
});
