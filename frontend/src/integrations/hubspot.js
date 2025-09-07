import { useState, useEffect } from 'react';
import {
    Box,
    Button,
    CircularProgress
} from '@mui/material';
import axios from 'axios';

export const HubspotIntegration = ({ user, org, integrationParams, setIntegrationParams }) => {
    const [isConnected, setIsConnected] = useState(false);//tracks whether the user has already authorized HubSpot
    const [isConnecting, setIsConnecting] = useState(false);//tracks whether the authorization process is in progress

    //sends a POST request to backend with the user and org ID-->responds with the HubSpot OAuth URL, opens popup window
    const handleConnectClick = async () => {
        try {
            setIsConnecting(true);
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/authorize`, formData);
            const authURL = response?.data;

            const newWindow = window.open(authURL, 'HubSpot Authorization', 'width=600, height=600');

            //polling timer to check when the user closes the window, runs function to fetch credentials
            const pollTimer = window.setInterval(() => {
                if (newWindow?.closed !== false) {
                    window.clearInterval(pollTimer);
                    handleWindowClosed();
                }
            }, 200);
        } catch (e) {
            setIsConnecting(false);
            alert(e?.response?.data?.detail || "Authorization failed");
        }
    };

    //retrieve the access token that was saved in Redis, and update global integrationParams object
    const handleWindowClosed = async () => {
        try {
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/credentials`, formData);
            const credentials = response.data;
            if (credentials) {
                setIsConnecting(false);
                setIsConnected(true);
                setIntegrationParams(prev => ({ ...prev, credentials: credentials, type: 'Hubspot' }));
            }
        } catch (e) {
            setIsConnecting(false);
            alert(e?.response?.data?.detail || "Failed to fetch credentials");
        }
    };

    //updates the button to show that the user is connected
    useEffect(() => {
        setIsConnected(integrationParams?.type === 'Hubspot' && integrationParams?.credentials ? true : false);
    }, []);

    return (
        <Box sx={{ mt: 2 }}>
            Parameters
            <Box display='flex' alignItems='center' justifyContent='center' sx={{ mt: 2 }}>
                <Button
                    variant='contained'
                    onClick={isConnected ? () => {} : handleConnectClick}
                    color={isConnected ? 'success' : 'primary'}
                    disabled={isConnecting}
                    style={{
                        pointerEvents: isConnected ? 'none' : 'auto',
                        cursor: isConnected ? 'default' : 'pointer',
                        opacity: isConnected ? 1 : undefined
                    }}
                >
                    {isConnected ? 'HubSpot Connected' : isConnecting ? <CircularProgress size={20} /> : 'Connect to HubSpot'}
                </Button>
            </Box>
        </Box>
    );
};