import { useEffect, useState } from "react";
import "./App.css";

const API_BASE =
  import.meta.env.VITE_API_BASE ||
  (import.meta.env.DEV
    ? "http://127.0.0.1:8000"
    : "/api");

const PRODUCT = {
  productId: "shoe_001",
  merchantId: "merchant_001",
  authorityId: "auth_001",
  name: "Running Shoes",
  size: 9,
  initialPrice: 3499,
  authorityLimit: 4000,
};


  /*
   * Main agentic-commerce entry point.
   *
   * The user gives natural language.
   * The backend agent:
   *   1. parses intent
   *   2. matches a product
   *   3. creates a proposal
   *   4. validates the proposal against authority
   *
   * No payment happens here.
   */
function App() {
  const [agentRequest, setAgentRequest] = useState(
    "Buy size-9 running shoes under ₹4,000"
  );

  const [agentLoading, setAgentLoading] = useState(false);
  const [agentResult, setAgentResult] = useState(null);

  const [currentPrice, setCurrentPrice] = useState(PRODUCT.initialPrice);
  const [merchantPrice, setMerchantPrice] = useState(PRODUCT.initialPrice);

  const [transactionId, setTransactionId] = useState(null);
  const [razorpayOrderId, setRazorpayOrderId] = useState(null);
  const [razorpayAmount, setRazorpayAmount] = useState(null);

  const [decision, setDecision] = useState("READY");
  const [reasons, setReasons] = useState([]);
  const [authorizedPrice, setAuthorizedPrice] = useState(
    PRODUCT.initialPrice
  );

  const [loading, setLoading] = useState(false);
  const [merchantLoading, setMerchantLoading] = useState(false);
  const [error, setError] = useState("");

  const priceChanged =
    transactionId !== null && currentPrice !== authorizedPrice;

  /*
   * Poll the backend for fresh transaction validation.
   *
   * Once Razorpay order creation starts, polling stops so the
   * validation result cannot overwrite EXECUTING/CAPTURED.
   */
  useEffect(() => {
    if (!transactionId || razorpayOrderId) {
      return;
    }

    const checkTransaction = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/transactions/revalidate`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              transaction_id: transactionId,
            }),
          }
        );

        if (!response.ok) {
          throw new Error("Unable to revalidate transaction.");
        }

        const data = await response.json();

        setCurrentPrice(data.current_price);
        setAuthorizedPrice(data.authorized_price);
        setDecision(data.decision);
        setReasons(data.reasons || []);
      } catch (err) {
        console.error(err);
      }
    };

    checkTransaction();

    const interval = setInterval(checkTransaction, 1000);

    return () => clearInterval(interval);
  }, [transactionId, razorpayOrderId]);

  const askAgent = async () => {
    setAgentLoading(true);
    setLoading(false);
    setError("");
    setReasons([]);
    setAgentResult(null);

    try {
      const response = await fetch(`${API_BASE}/agent/purchase`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          request: agentRequest,
          authority_id: PRODUCT.authorityId,
          product_ids: [PRODUCT.productId],
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Agent could not process the request."
        );
      }

      setAgentResult(data);

      setTransactionId(data.transaction_id);
      setRazorpayOrderId(null);
      setRazorpayAmount(null);

      setAuthorizedPrice(
        data.proposal?.amount ?? PRODUCT.initialPrice
      );

      setCurrentPrice(
        data.product?.price ?? PRODUCT.initialPrice
      );

      setMerchantPrice(
        data.product?.price ?? PRODUCT.initialPrice
      );

      setDecision(data.decision || data.state || "READY");
      setReasons(data.reasons || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setAgentLoading(false);
    }
  };

  /*
   * Legacy/manual checkout path is intentionally retained.
   *
   * This gives the demo a direct transaction-start path while
   * the primary UX uses the agent endpoint.
   */
  const startCheckout = async () => {
    setLoading(true);
    setError("");
    setReasons([]);

    try {
      const response = await fetch(`${API_BASE}/transactions/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          authority_id: PRODUCT.authorityId,
          proposal: {
            action: "PURCHASE",
            product_id: PRODUCT.productId,
            merchant_id: PRODUCT.merchantId,
            amount: currentPrice,
            currency: "INR",
            quantity: 1,
          },
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Checkout could not be started."
        );
      }

      if (data.state !== "AUTHORIZED") {
        setTransactionId(null);
        setRazorpayOrderId(null);
        setRazorpayAmount(null);

        setAuthorizedPrice(PRODUCT.initialPrice);
        setCurrentPrice(data.current_price ?? currentPrice);
        setDecision(data.decision || "BLOCK");

        setReasons(
          data.reasons || [
            "Transaction did not pass initial authorization.",
          ]
        );

        return;
      }

      setTransactionId(data.transaction_id);
      setRazorpayOrderId(null);
      setRazorpayAmount(null);

      setAuthorizedPrice(data.authorized_price);
      setCurrentPrice(data.current_price);
      setDecision(data.decision || "ALLOW");

      setAgentResult(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /*
   * Final money-movement request.
   *
   * The frontend does not decide whether payment is safe.
   * The backend performs final server-side revalidation.
   */
  const executePayment = async () => {
    if (!transactionId) {
      return;
    }

    setLoading(true);
    setError("");
    setReasons([]);

    try {
      const response = await fetch(
        `${API_BASE}/transactions/execute`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            transaction_id: transactionId,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Payment execution failed."
        );
      }

      setDecision(data.decision || data.state);

      setCurrentPrice(
        data.current_price ?? currentPrice
      );

      setReasons(data.reasons || []);

      if (data.state === "BLOCKED") {
        setRazorpayOrderId(null);
        setRazorpayAmount(null);

        setError(
          "AgentGuard stopped the payment before Razorpay was called."
        );

        return;
      }

      if (data.state === "EXECUTING") {
        setRazorpayOrderId(data.order_id);
        setRazorpayAmount(data.amount);

        setError("");

        setReasons([
          "AgentGuard authorized the transaction.",
          "Final server-side revalidation passed.",
          "Razorpay order created successfully.",
          "Payment is waiting for Razorpay Checkout.",
        ]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /*
   * Opens Razorpay Checkout after AgentGuard has created
   * a valid Razorpay order.
   */
  const openRazorpayCheckout = () => {
    if (!razorpayOrderId || !razorpayAmount) {
      setError("Razorpay order is not ready yet.");
      return;
    }

    if (!window.Razorpay) {
      setError(
        "Razorpay Checkout failed to load. Please refresh the page."
      );
      return;
    }

    const options = {
      key: import.meta.env.VITE_RAZORPAY_KEY_ID,

      amount: razorpayAmount,

      currency: "INR",

      name: "AgentGuard",

      description:
        "Agent-authorized Running Shoes purchase",

      order_id: razorpayOrderId,

      handler: async function (response) {
        setLoading(true);
        setError("");
        setReasons([]);

        try {
          const verifyResponse = await fetch(
            `${API_BASE}/transactions/verify-payment`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                transaction_id: transactionId,
                razorpay_payment_id:
                  response.razorpay_payment_id,
                razorpay_order_id:
                  response.razorpay_order_id,
                razorpay_signature:
                  response.razorpay_signature,
              }),
            }
          );

          const data = await verifyResponse.json();

          if (!verifyResponse.ok) {
            throw new Error(
              data.detail ||
                "Payment verification failed."
            );
          }

          if (!data.verified) {
            throw new Error(
              data.message ||
                "AgentGuard could not verify the payment."
            );
          }

          setDecision("CAPTURED");

          setReasons([
            "Razorpay Checkout completed.",
            "Payment signature verified server-side.",
            "Razorpay order matched the AgentGuard transaction.",
            "Transaction marked CAPTURED.",
          ]);

          setError("");
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      },

      modal: {
        ondismiss: function () {
          setError(
            "Razorpay Checkout was closed before payment completed."
          );
        },
      },
    };

    const razorpay = new window.Razorpay(options);

    razorpay.on(
      "payment.failed",
      function (response) {
        console.error(
          "Razorpay payment failed:",
          response
        );

        setError(
          "Razorpay reported a payment failure."
        );

        setReasons([
          "Razorpay Checkout was reached.",
          "Razorpay reported payment failure.",
          "AgentGuard did not mark the transaction CAPTURED.",
        ]);
      }
    );

    razorpay.open();
  };

  /*
   * Merchant simulator.
   *
   * This deliberately mutates merchant state after the agent
   * has received authorization, allowing us to demonstrate
   * stale authorization being blocked.
   */
  const updateMerchantPrice = async () => {
    setMerchantLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE}/merchant/products/${PRODUCT.productId}/price`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            price: Number(merchantPrice),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to update merchant price."
        );
      }

      setCurrentPrice(data.current_price);
    } catch (err) {
      setError(err.message);
    } finally {
      setMerchantLoading(false);
    }
  };

  /*
   * Reset only the frontend state.
   *
   * The backend seed/reload behavior remains responsible for
   * restoring demo merchant state.
   */
  const resetDemo = () => {
    setAgentRequest(
      "Buy size-9 running shoes under ₹4,000"
    );

    setAgentResult(null);

    setTransactionId(null);
    setRazorpayOrderId(null);
    setRazorpayAmount(null);

    setDecision("READY");
    setReasons([]);

    setAuthorizedPrice(PRODUCT.initialPrice);
    setCurrentPrice(PRODUCT.initialPrice);
    setMerchantPrice(PRODUCT.initialPrice);

    setError("");
  };

  const product = agentResult?.product || {
    product_id: PRODUCT.productId,
    merchant_id: PRODUCT.merchantId,
    name: PRODUCT.name,
    category: "shoes",
    price: currentPrice,
    currency: "INR",
    available_sizes: [8, 9, 10],
    inventory: 5,
  };

  const intent = agentResult?.intent;

  const proposal = agentResult?.proposal;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand">
            <span className="brand-mark">AG</span>
            <span>AgentGuard</span>
          </div>

          <p className="subtitle">
            Runtime Control Plane for Agentic Payments
          </p>
        </div>

        <div className="principle">
          <span>AI proposes.</span>
          <strong>
            Deterministic systems control money.
          </strong>
        </div>
      </header>

      <main className="dashboard">
        <section className="hero">
          <div>
            <div className="eyebrow">
              AGENTIC COMMERCE DEMO
            </div>

            <h1>
              Bounded authority.
              <br />
              Verified at payment time.
            </h1>

            <p>
              An AI agent can propose a purchase, but
              AgentGuard revalidates the transaction immediately
              before money moves.
            </p>
          </div>

          <div className="security-badge">
            <span className="pulse-dot"></span>

            <div>
              <small>CONTROL PLANE</small>
              <strong>ACTIVE</strong>
            </div>
          </div>
        </section>

        {/* =====================================================
            AGENT REQUEST
        ====================================================== */}
        <section className="card agent-card">
          <div className="card-header">
            <div>
              <span className="card-label">
                AGENT REQUEST
              </span>

              <h2>Tell the agent what to buy</h2>
            </div>

            <span className="simulator-tag">
              NATURAL LANGUAGE
            </span>
          </div>

          <p className="agent-description">
            The agent interprets the user's request and creates
            a bounded transaction proposal. It cannot directly
            move money.
          </p>

          <div className="agent-input-row">
            <input
              className="agent-input"
              value={agentRequest}
              onChange={(event) =>
                setAgentRequest(event.target.value)
              }
              placeholder="e.g. Buy size-9 running shoes under ₹4,000"
              disabled={agentLoading || !!razorpayOrderId}
            />

            <button
              className="agent-button"
              onClick={askAgent}
              disabled={
                agentLoading ||
                !agentRequest.trim() ||
                !!razorpayOrderId
              }
            >
              {agentLoading
                ? "Thinking..."
                : "Ask Agent"}
            </button>
          </div>

          <div className="agent-example">
            <span>TRY</span>
            <button
              onClick={() =>
                setAgentRequest(
                  "Buy size-9 running shoes under ₹4,000"
                )
              }
            >
              Buy size-9 running shoes under ₹4,000
            </button>
          </div>

          {agentResult && (
            <div className="agent-analysis">
              <div className="analysis-header">
                <div>
                  <span className="card-label">
                    AGENT OUTPUT
                  </span>

                  <strong>
                    Proposal created — payment not executed
                  </strong>
                </div>

                <span className="status-pill">
                  {agentResult.state}
                </span>
              </div>

              <div className="analysis-grid">
                <div>
                  <span>INTERPRETED CATEGORY</span>
                  <strong>
                    {intent?.category || "—"}
                  </strong>
                </div>

                <div>
                  <span>REQUESTED SIZE</span>
                  <strong>
                    {intent?.size ?? "Any"}
                  </strong>
                </div>

                <div>
                  <span>USER MAXIMUM</span>
                  <strong>
                    ₹
                    {intent?.max_amount?.toLocaleString(
                      "en-IN"
                    ) || "—"}
                  </strong>
                </div>

                <div>
                  <span>PROPOSED AMOUNT</span>
                  <strong>
                    ₹
                    {proposal?.amount?.toLocaleString(
                      "en-IN"
                    ) || "—"}
                  </strong>
                </div>
              </div>
            </div>
          )}
        </section>

        <div className="grid">
          {/* =====================================================
              CUSTOMER CHECKOUT
          ====================================================== */}
          <section className="card checkout-card">
            <div className="card-header">
              <div>
                <span className="card-label">
                  CUSTOMER CHECKOUT
                </span>

                <h2>Agent-selected product</h2>
              </div>

              <span className="status-pill">
                {decision}
              </span>
            </div>

            <div className="product">
              <div className="product-image">👟</div>

              <div className="product-info">
                <h3>{product.name}</h3>

                <p>
                  Size{" "}
                  {intent?.size ?? PRODUCT.size}
                  {" · "}
                  Quantity{" "}
                  {proposal?.quantity ?? 1}
                </p>

                <span>
                  Merchant: {product.merchant_id}
                </span>
              </div>

              <div className="price">
                <small>CURRENT PRICE</small>

                <strong>
                  ₹{currentPrice.toLocaleString("en-IN")}
                </strong>
              </div>
            </div>

            <div className="authority-box">
              <div className="authority-title">
                <span>🛡</span>

                <strong>Authority Envelope</strong>
              </div>

              <div className="authority-grid">
                <div>
                  <span>Maximum allowed</span>

                  <strong>
                    ₹
                    {PRODUCT.authorityLimit.toLocaleString(
                      "en-IN"
                    )}
                  </strong>
                </div>

                <div>
                  <span>Authorized price</span>

                  <strong>
                    ₹
                    {authorizedPrice.toLocaleString(
                      "en-IN"
                    )}
                  </strong>
                </div>

                <div>
                  <span>Merchant</span>

                  <strong>
                    {product.merchant_id}
                  </strong>
                </div>

                <div>
                  <span>Authority ID</span>

                  <strong>
                    {PRODUCT.authorityId}
                  </strong>
                </div>
              </div>
            </div>

            {priceChanged && (
              <div className="warning">
                <div className="warning-icon">!</div>

                <div>
                  <strong>
                    Price changed — payment blocked
                  </strong>

                  <p>
                    Authorized at ₹
                    {authorizedPrice.toLocaleString(
                      "en-IN"
                    )}
                    , but the merchant now charges ₹
                    {currentPrice.toLocaleString(
                      "en-IN"
                    )}
                    .
                  </p>
                </div>
              </div>
            )}

            {decision === "ALLOW" &&
              transactionId &&
              !priceChanged && (
                <div className="success">
                  <div className="success-icon">✓</div>

                  <div>
                    <strong>
                      Transaction revalidated
                    </strong>

                    <p>
                      The current merchant state still
                      matches the authority envelope.
                    </p>
                  </div>
                </div>
              )}

            {reasons.length > 0 && (
              <div className="reason-box">
                <strong>
                  AgentGuard decision reasons
                </strong>

                <ul>
                  {reasons.map((reason, index) => (
                    <li key={index}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}

            {error && (
              <div className="error-box">
                {error}
              </div>
            )}

            <div className="actions">
              {!transactionId ? (
                <button
                  className="primary-button"
                  onClick={
                    agentResult
                      ? executePayment
                      : startCheckout
                  }
                  disabled={loading || agentLoading}
                >
                  {loading
                    ? "Processing..."
                    : agentResult
                      ? "Pay ₹" +
                        authorizedPrice.toLocaleString(
                          "en-IN"
                        )
                      : "Authorize Checkout"}
                </button>
              ) : (
                <>
                  {!razorpayOrderId && (
                    <button
                      className="primary-button"
                      onClick={executePayment}
                      disabled={loading}
                    >
                      {loading
                        ? "Processing..."
                        : "Pay ₹" +
                          authorizedPrice.toLocaleString(
                            "en-IN"
                          )}
                    </button>
                  )}

                  {razorpayOrderId && (
                    <button
                      className="primary-button"
                      onClick={openRazorpayCheckout}
                      disabled={loading}
                    >
                      {loading
                        ? "Verifying..."
                        : "Open Razorpay Checkout"}
                    </button>
                  )}

                  <button
                    className="secondary-button"
                    onClick={resetDemo}
                  >
                    Reset Demo
                  </button>
                </>
              )}
            </div>

            {razorpayOrderId && (
              <div className="transaction-id">
                Razorpay Order{" "}
                <code>{razorpayOrderId}</code>
              </div>
            )}

            {transactionId && (
              <div className="transaction-id">
                Transaction{" "}
                <code>{transactionId}</code>
              </div>
            )}
          </section>

          {/* =====================================================
              MERCHANT SIMULATOR
          ====================================================== */}
          <section className="card merchant-card">
            <div className="card-header">
              <div>
                <span className="card-label">
                  MERCHANT SIMULATOR
                </span>

                <h2>Change the merchant state</h2>
              </div>

              <span className="simulator-tag">
                TEST MODE
              </span>
            </div>

            <p className="merchant-description">
              Simulate a merchant changing the price after
              the agent has already received authorization.
              AgentGuard must detect the stale authorization
              before money moves.
            </p>

            <div className="merchant-product">
              <div>
                <span>Running Shoes</span>

                <strong>
                  ₹{currentPrice.toLocaleString("en-IN")}
                </strong>
              </div>
            </div>

            <label htmlFor="merchant-price">
              New merchant price
            </label>

            <div className="price-input">
              <span>₹</span>

              <input
                id="merchant-price"
                type="number"
                min="1"
                value={merchantPrice}
                onChange={(event) =>
                  setMerchantPrice(event.target.value)
                }
              />
            </div>

            <button
              className="merchant-button"
              onClick={updateMerchantPrice}
              disabled={merchantLoading}
            >
              {merchantLoading
                ? "Updating..."
                : "Update Merchant Price"}
            </button>

            <div className="demo-hint">
              <strong>🔥 Try the attack path</strong>

              <ol>
                <li>
                  Ask the agent to buy size-9 shoes under
                  ₹4,000.
                </li>

                <li>
                  Agent authorizes the ₹3,499 proposal.
                </li>

                <li>
                  Change merchant price to ₹4,799.
                </li>

                <li>
                  Watch AgentGuard detect the mismatch.
                </li>

                <li>
                  Try to pay — the backend blocks it.
                </li>
              </ol>
            </div>
          </section>
        </div>


        {/* =====================================================
            SECURITY EVALUATION
        ====================================================== */}
        <section className="security-evaluation">
          <div className="section-header">
            <div>
              <span className="eyebrow">SECURITY EVALUATION</span>
              <h2>What happens when the agent crosses the boundary?</h2>
              <p>
                AgentGuard revalidates delegated authority against fresh
                merchant state before money moves.
              </p>
            </div>

            <div className="evaluation-score">
              <strong>8 / 8</strong>
              <span>controls enforced</span>
            </div>
          </div>

          <div className="security-grid">
            <SecurityScenario
              status="allowed"
              title="Valid purchase"
              detail="₹3,499 within ₹4,000 authority"
            />
            <SecurityScenario
              status="blocked"
              title="Price changed"
              detail="₹3,499 → ₹4,799"
            />
            <SecurityScenario
              status="blocked"
              title="Over-authority amount"
              detail="Agent proposes ₹5,000"
            />
            <SecurityScenario
              status="blocked"
              title="Unauthorized merchant"
              detail="Merchant binding violated"
            />
            <SecurityScenario
              status="blocked"
              title="Unauthorized product"
              detail="Product binding violated"
            />
            <SecurityScenario
              status="blocked"
              title="Inventory unavailable"
              detail="Available inventory: 0"
            />
            <SecurityScenario
              status="blocked"
              title="Expired authority"
              detail="Delegated authority expired"
            />
            <SecurityScenario
              status="blocked"
              title="Unauthorized execution"
              detail="Transaction was not AUTHORIZED"
            />
          </div>
        </section>

        {/* =====================================================
            MONEY MOVEMENT CONTROL
        ====================================================== */}
        <section className="flow-card">
          <div className="flow-title">
            <span className="card-label">
              MONEY MOVEMENT CONTROL
            </span>

            <h2>What happens before payment?</h2>
          </div>

          <div className="flow">
            <FlowStep
              number="01"
              title="AI proposes"
              description="Natural-language intent becomes a transaction proposal."
              active
            />

            <div className="flow-line"></div>

            <FlowStep
              number="02"
              title="Authority check"
              description="Action, merchant, product and amount are bounded."
              active={!!transactionId}
            />

            <div className="flow-line"></div>

            <FlowStep
              number="03"
              title="Final revalidation"
              description="Fresh merchant state is checked immediately before payment."
              active={
                decision === "ALLOW" ||
                decision === "EXECUTING" ||
                decision === "CAPTURED" ||
                decision === "BLOCK"
              }
            />

            <div className="flow-line"></div>

            <FlowStep
              number="04"
              title="Razorpay"
              description="Only a valid, freshly revalidated transaction can execute."
              active={
                decision === "EXECUTING" ||
                decision === "CAPTURED"
              }
            />
          </div>
        </section>
      </main>

      <footer>
        <span>AgentGuard v0.1.0</span>

        <span>
          Every money action is bounded, explainable and gated.
        </span>
      </footer>
    </div>
  );
}


function SecurityScenario({
  status,
  title,
  detail,
}) {
  const isAllowed = status === "allowed";

  return (
    <div className={`security-scenario ${status}`}>
      <div className="scenario-status">
        <span className="status-dot"></span>
        <span>{isAllowed ? "ALLOWED" : "BLOCKED"}</span>
      </div>

      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

function FlowStep({
  number,
  title,
  description,
  active,
}) {
  return (
    <div
      className={`flow-step ${
        active ? "active" : ""
      }`}
    >
      <div className="flow-number">
        {number}
      </div>

      <strong>{title}</strong>

      <p>{description}</p>
    </div>
  );
}

export default App;