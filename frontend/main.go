package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/pkg/model"
	"github.com/cloudwego/eino/pkg/schema"
)

// Minimal Azure OpenAI REST client
type AzureOpenAIClient struct {
	Endpoint   string
	Deployment string
	APIKey     string
	Client     *http.Client
}

func NewAzureOpenAIClient(endpoint, deployment, apiKey string, timeout time.Duration) *AzureOpenAIClient {
	return &AzureOpenAIClient{
		Endpoint:   endpoint,
		Deployment: deployment,
		APIKey:     apiKey,
		Client:     &http.Client{Timeout: timeout},
	}
}

type azureChatRequest struct {
	Messages  []map[string]string `json:"messages"`
	MaxTokens int                 `json:"max_tokens,omitempty"`
}

type azureChatChoice struct {
	Message map[string]string `json:"message"`
}

type azureChatResponse struct {
	Choices []azureChatChoice `json:"choices"`
}

func (c *AzureOpenAIClient) CallChatCompletion(ctx context.Context, messages []*schema.Message) (string, error) {
	if c.Endpoint == "" || c.Deployment == "" {
		return "", errors.New("endpoint or deployment not set")
	}
	url := fmt.Sprintf("%s/openai/deployments/%s/chat/completions?api-version=2025-04-01-preview", c.Endpoint, c.Deployment)

	reqBody := azureChatRequest{Messages: make([]map[string]string, 0, len(messages)), MaxTokens: 800}
	for _, m := range messages {
		reqBody.Messages = append(reqBody.Messages, map[string]string{"role": string(m.Role), "content": m.Content})
	}

	b, _ := json.Marshal(reqBody)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, io.NopCloser(bytesReader(b)))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")
	if c.APIKey != "" {
		req.Header.Set("api-key", c.APIKey)
	}

	resp, err := c.Client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("azure openai error status=%d body=%s", resp.StatusCode, string(body))
	}

	var ar azureChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&ar); err != nil {
		return "", err
	}
	if len(ar.Choices) == 0 {
		return "", errors.New("no choices returned")
	}
	content := ar.Choices[0].Message["content"]
	return content, nil
}

// tiny bytes reader wrapper to avoid importing bytes
type readerWrapper struct {
	b []byte
	i int
}

func bytesReader(b []byte) *readerWrapper { return &readerWrapper{b: b} }
func (r *readerWrapper) Read(p []byte) (n int, err error) {
	if r.i >= len(r.b) {
		return 0, io.EOF
	}
	n = copy(p, r.b[r.i:])
	r.i += n
	return n, nil
}

// AzureChatModel implements model.BaseChatModel
type AzureChatModel struct{ Client *AzureOpenAIClient }

func (m *AzureChatModel) Generate(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.Message, error) {
	text, err := m.Client.CallChatCompletion(ctx, input)
	if err != nil {
		return nil, err
	}
	return schema.AssistantMessage(text), nil
}

func (m *AzureChatModel) Stream(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.StreamReader[*schema.Message], error) {
	return nil, errors.New("stream not implemented")
}

func (m *AzureChatModel) BindTools(tools []*schema.ToolInfo) error { return nil }

func main() {
	// flags and envs
	var (
		defaultEndpoint   = ""
		defaultAPIKey     = ""
		defaultDeployment = ""
	)
	endpoint := flag.String("endpoint", os.Getenv("AZURE_OPENAI_ENDPOINT"), "Azure OpenAI endpoint")
	deployment := flag.String("deployment", os.Getenv("AZURE_OPENAI_DEPLOYMENT"), "Azure deployment name")
	apiKey := flag.String("apikey", os.Getenv("AZURE_OPENAI_API_KEY"), "Azure OpenAI API key")
	timeout := flag.Int("timeout", 30, "request timeout seconds")
	flag.Parse()

	if *endpoint == "" {
		*endpoint = defaultEndpoint
	}
	if *deployment == "" {
		*deployment = defaultDeployment
	}
	if *apiKey == "" {
		*apiKey = defaultAPIKey
	}

	client := NewAzureOpenAIClient(*endpoint, *deployment, *apiKey, time.Duration(*timeout)*time.Second)
	modelNode := &AzureChatModel{Client: client}

	chain := compose.NewChain[[]*schema.Message, *schema.Message]()
	chain.AppendChatModel(modelNode)

	ctx := context.Background()
	runnable, err := chain.Compile(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "compile error: %v\n", err)
		os.Exit(1)
	}

	input := []*schema.Message{schema.UserMessage("Say hello to Eino via AzureOpenAI GPT-5-mini")}
	out, err := runnable.Invoke(ctx, input)
	if err != nil {
		fmt.Fprintf(os.Stderr, "invoke error: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("Model output:\n", out.Content)
}
