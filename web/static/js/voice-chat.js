class VoiceChat {
    constructor(classroomId, userId, isTeacher) {
        this.classroomId = classroomId;
        this.userId = userId;
        this.isTeacher = isTeacher;
        this.peerConnections = new Map(); // userId -> RTCPeerConnection
        this.localStream = null;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.socket = null;
        this.mediaConstraints = {
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            },
            video: false
        };
        this.configuration = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' },
            ]
        };
        
        // Voice activity detection
        this.vadEnabled = true;
        this.silenceDelay = 500;
        this.silenceThreshold = -50;
        this.speaking = false;
    }

    async initialize() {
        try {
            console.log('Initializing voice chat...');
            // Get user media
            console.log('Requesting microphone access...');
            this.localStream = await navigator.mediaDevices.getUserMedia(this.mediaConstraints);
            console.log('Microphone access granted');
            
            // Setup voice activity detection
            console.log('Setting up voice activity detection...');
            this.setupVAD();
            
            // Connect to signaling server
            console.log('Connecting to signaling server...');
            this.connectSignaling();
            
            // Initial mute state
            const initialMuteState = !this.isTeacher;
            console.log(`Setting initial mute state: ${initialMuteState}`);
            this.setMicrophoneMute(initialMuteState);
            
            return true;
        } catch (error) {
            console.error('Error initializing voice chat:', error);
            if (error.name === 'NotAllowedError') {
                console.error('Microphone access was denied by the user');
            } else if (error.name === 'NotFoundError') {
                console.error('No microphone found');
            }
            return false;
        }
    }

    setupVAD() {
        const audioSource = this.audioContext.createMediaStreamSource(this.localStream);
        const analyser = this.audioContext.createAnalyser();
        analyser.fftSize = 512;
        analyser.smoothingTimeConstant = 0.1;
        audioSource.connect(analyser);

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Float32Array(bufferLength);
        let silenceStart = Date.now();

        const checkAudioLevel = () => {
            if (!this.vadEnabled) return;

            analyser.getFloatFrequencyData(dataArray);
            const average = dataArray.reduce((a, b) => a + b) / bufferLength;
            const speaking = average > this.silenceThreshold;

            if (speaking && !this.speaking) {
                this.speaking = true;
                this.onVoiceActivityStart();
            } else if (!speaking && this.speaking && Date.now() - silenceStart > this.silenceDelay) {
                this.speaking = false;
                this.onVoiceActivityEnd();
            }

            if (!speaking) {
                silenceStart = Date.now();
            }
        };

        setInterval(checkAudioLevel, 100);
    }

    connectSignaling() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/voice/${this.classroomId}/`;
        console.log('Connecting to WebSocket URL:', wsUrl);
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('Connected to signaling server');
            // Send initial join message
            this.socket.send(JSON.stringify({
                type: 'join',
                userId: this.userId,
                isTeacher: this.isTeacher
            }));
        };
        
        this.socket.onmessage = async (event) => {
            const data = JSON.parse(event.data);
            console.log('Received WebSocket message:', data);
            await this.handleSignalingMessage(data);
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.socket.onclose = (event) => {
            console.log('Disconnected from signaling server', event.code, event.reason);
            // Attempt to reconnect after 5 seconds
            setTimeout(() => this.connectSignaling(), 5000);
        };
    }

    async handleSignalingMessage(data) {
        switch (data.type) {
            case 'user-joined':
                await this.handleUserJoined(data.userId);
                break;
            case 'user-left':
                this.handleUserLeft(data.userId);
                break;
            case 'offer':
                await this.handleOffer(data.userId, data.offer);
                break;
            case 'answer':
                await this.handleAnswer(data.userId, data.answer);
                break;
            case 'ice-candidate':
                await this.handleIceCandidate(data.userId, data.candidate);
                break;
        }
    }

    async handleUserJoined(userId) {
        if (userId === this.userId) return;
        
        const pc = new RTCPeerConnection(this.configuration);
        this.peerConnections.set(userId, pc);
        
        // Add local stream
        this.localStream.getTracks().forEach(track => {
            pc.addTrack(track, this.localStream);
        });
        
        // Handle ICE candidates
        pc.onicecandidate = (event) => {
            if (event.candidate) {
                this.socket.send(JSON.stringify({
                    type: 'ice-candidate',
                    userId: userId,
                    candidate: event.candidate
                }));
            }
        };
        
        // Handle remote stream
        pc.ontrack = (event) => {
            this.handleRemoteStream(userId, event.streams[0]);
        };
        
        // Create and send offer if we're the teacher
        if (this.isTeacher) {
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            this.socket.send(JSON.stringify({
                type: 'offer',
                userId: userId,
                offer: offer
            }));
        }
    }

    handleUserLeft(userId) {
        const pc = this.peerConnections.get(userId);
        if (pc) {
            pc.close();
            this.peerConnections.delete(userId);
        }
        
        // Remove remote audio element
        const audioElement = document.getElementById(`remote-audio-${userId}`);
        if (audioElement) {
            audioElement.remove();
        }
    }

    async handleOffer(userId, offer) {
        if (!this.peerConnections.has(userId)) {
            await this.handleUserJoined(userId);
        }
        
        const pc = this.peerConnections.get(userId);
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        
        this.socket.send(JSON.stringify({
            type: 'answer',
            userId: userId,
            answer: answer
        }));
    }

    async handleAnswer(userId, answer) {
        const pc = this.peerConnections.get(userId);
        if (pc) {
            await pc.setRemoteDescription(new RTCSessionDescription(answer));
        }
    }

    async handleIceCandidate(userId, candidate) {
        const pc = this.peerConnections.get(userId);
        if (pc) {
            await pc.addIceCandidate(new RTCIceCandidate(candidate));
        }
    }

    handleRemoteStream(userId, stream) {
        console.log('Handling remote stream from user:', userId);
        let audioElement = document.getElementById(`remote-audio-${userId}`);
        if (!audioElement) {
            console.log('Creating new audio element for user:', userId);
            audioElement = document.createElement('audio');
            audioElement.id = `remote-audio-${userId}`;
            audioElement.autoplay = true;
            audioElement.controls = true; // Add controls for debugging
            document.body.appendChild(audioElement);
        }
        audioElement.srcObject = stream;
        
        // Add event listeners for debugging
        audioElement.onplay = () => console.log('Audio started playing for user:', userId);
        audioElement.onpause = () => console.log('Audio paused for user:', userId);
        audioElement.onerror = (e) => console.error('Audio error for user:', userId, e);
    }

    setMicrophoneMute(muted) {
        this.localStream.getAudioTracks().forEach(track => {
            track.enabled = !muted;
        });
    }

    onVoiceActivityStart() {
        // Update UI to show speaking indicator
        document.dispatchEvent(new CustomEvent('voice-activity-start', {
            detail: { userId: this.userId }
        }));
    }

    onVoiceActivityEnd() {
        // Update UI to hide speaking indicator
        document.dispatchEvent(new CustomEvent('voice-activity-end', {
            detail: { userId: this.userId }
        }));
    }

    disconnect() {
        // Close all peer connections
        this.peerConnections.forEach(pc => pc.close());
        this.peerConnections.clear();
        
        // Stop local stream tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        
        // Close signaling connection
        if (this.socket) {
            this.socket.close();
        }
        
        // Close audio context
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
}
